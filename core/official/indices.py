"""Borsa İstanbul official end-of-day index values (K madde 8, the user's 11.11.2026 decision; level 1).

The user downloads DataStore's "Gün Sonu Endeks ve İşlem Hacmi" monthly folders into data/inbox/bist_endeks/YYYYMM.
Read only, never changed; not in git or the daily backup. Formats (found on 11.11.2026 in all 466 folders):
- until 10.2015 and the first half of 11.2015 (BISTECH_Oncesi_...): one file a month, one row per session, the
  price and the return index on the same row, dates 04.01.2010, UTF-8;
- 11.2015: a title, an empty line and a "Türkçe / English" header, dates 30/11/2015, an empty third column;
- 12.2015–08.2019: the same in UTF-16 (02.2016 has a .txt extension); 09.2019–: PP_GUNSONUENDEKS_M.csv with the
  English names as an extra column. The return index is its own row (XU100_CFNNTLTL, type "Getiri").
  The leveraged and risk control files are not read.
Index points were rescaled ÷ 100 on 02.01.1997 and on 01.07.2020 in these files (SCALE_STEPS; the request named
only 27.07.2020, which would also divide 01–24.07.2020 twice). Index
points did not change on 01.01.2005 (29.12.2004 24.971,68; 03.01.2005 25.445,15); lira values did (÷ 1 000 000)."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from core.config.paths import DATA_DIR
from core.infrastructure.logger import get_logger
from core.official import prices

logger = get_logger(__name__)

INBOX = DATA_DIR / "inbox" / "bist_endeks"
KEEP = frozenset({"XU100", "XU030", "XU050", "XUTUM", "XBANK", "XUSIN", "XUHIZ", "XUMAL", "XHOLD"})
RETURN_SUFFIX = "_CFNNTLTL"
# Index points were rescaled twice in these files: ÷ 100 from 02.01.1997 (27.12.1996 XU100 97.588,81;
# 02.01.1997 988,93) and ÷ 100 from 01.07.2020 (30.06.2020 116.524,78; 01.07.2020 1.153,15). Points before each
# step are divided by its factor, so the series has today's scale (found on 11.11.2026 by searching for jumps).
SCALE_STEPS = ((date(1997, 1, 2), 100), (date(2020, 7, 1), 100))
LIRA_UNTIL = date(2005, 1, 1)
LIRA = 1_000_000

_TR = str.maketrans("ŞĞİÜÖÇ", "SGIUOC")


def _norm(name: str) -> str:
    name = name.split("/")[0]
    return re.sub(r"\s+", " ", name.strip().upper().translate(_TR))


OLD = frozenset({"TARIH", "SEANS NO", "ENDEKS KODU", "FIYAT ENDEKSI BOLEN DEGERI", "GETIRI ENDEKSI BOLEN DEGERI",
                 "FIYAT ENDEKSI KAPANIS DEGERI", "FIYAT ENDEKSI MINIMUM DEGERI", "FIYAT ENDEKSI MAXIMUM DEGERI",
                 "GETIRI ENDEKSI KAPANIS DEGERI", "FIYAT ENDEKSI ACILIS SEANSI DEGERI", "ISLEM HACMI",
                 "ISLEM MIKTARI"})
NEW = frozenset({"TARIH", "ENDEKS KODU", "ENDEKSLER", "ENDEKSLERIN INGILIZCE ISIMLERI", "ENDEKS TURU", "BOLEN",
                 "KAPANIS DEGERI", "EN DUSUK", "EN YUKSEK", "ISLEM HACMI", "ISLEM MIKTARI", ""})
REQUIRED = {"eski": ("TARIH", "SEANS NO", "ENDEKS KODU", "FIYAT ENDEKSI KAPANIS DEGERI"),
            "yeni": ("TARIH", "ENDEKS KODU", "ENDEKS TURU", "KAPANIS DEGERI", "EN DUSUK", "EN YUKSEK")}


@dataclass(frozen=True)
class Row:
    code: str
    day: date
    close: float
    low: float
    high: float
    return_close: float | None
    value: float


@dataclass
class FileResult:
    name: str
    rows: list[Row] = field(default_factory=list)
    rejected: str | None = None


def _day(text: str) -> date:
    text = text.strip()
    return datetime.strptime(text, "%d/%m/%Y" if "/" in text else "%d.%m.%Y").date()


def _scale(day: date, value: float | None) -> float | None:
    if value is None:
        return None
    for step, factor in SCALE_STEPS:
        if day < step:
            value /= factor
    return value


def _lira(day: date, value: float | None) -> float:
    value = value or 0.0
    return value / LIRA if day < LIRA_UNTIL else value


def read_file(path: Path) -> FileResult:
    path = Path(path)
    result = FileResult(path.name)
    lines = prices._decode(path.read_bytes()).splitlines()
    at = next((i for i, line in enumerate(lines[:10]) if _norm(line.split(";")[0]) == "TARIH"), None)
    if at is None:
        result.rejected = "başlık satırı yok (TARIH)"
        return result
    header = [_norm(h) for h in lines[at].split(";")]
    system = "eski" if "SEANS NO" in header else "yeni"
    unknown = [h for h in header if h not in (OLD if system == "eski" else NEW)]
    if unknown:
        result.rejected = f"bilinmeyen başlık ({system} sistem): {', '.join(unknown)}"
        return result
    missing = [h for h in REQUIRED[system] if h not in header]
    if missing:
        result.rejected = f"eksik alan ({system} sistem): {', '.join(missing)}"
        return result
    col = {h: i for i, h in enumerate(header) if h}

    def get(cells, name):
        i = col.get(name)
        return cells[i] if i is not None and i < len(cells) else ""

    body = [line.split(";") for line in lines[at + 1:] if line.strip()]
    body = [c for c in body if not _norm(c[0]).startswith("DATE")]
    if system == "yeni":
        found: dict[tuple[str, date], dict] = {}
        for cells in body:
            code = get(cells, "ENDEKS KODU").strip()
            base = code[: -len(RETURN_SUFFIX)] if code.endswith(RETURN_SUFFIX) else code
            if base not in KEEP:
                continue
            day = _day(get(cells, "TARIH"))
            close = prices._num(get(cells, "KAPANIS DEGERI"))
            if not close:
                continue
            item = found.setdefault((base, day), {})
            if code != base:
                item["return_close"] = _scale(day, close)
            else:
                item.update(close=_scale(day, close), low=_scale(day, prices._num(get(cells, "EN DUSUK")) or close),
                            high=_scale(day, prices._num(get(cells, "EN YUKSEK")) or close),
                            value=_lira(day, prices._num(get(cells, "ISLEM HACMI"))))
        for (code, day), item in sorted(found.items(), key=lambda kv: (kv[0][1], kv[0][0])):
            if "close" in item:
                result.rows.append(Row(code, day, item["close"], item["low"], item["high"],
                                       item.get("return_close"), item["value"]))
        return result

    sessions: dict[tuple[str, date], list[tuple[int, list[str]]]] = defaultdict(list)
    for cells in body:
        code = get(cells, "ENDEKS KODU").strip()
        if code in KEEP:
            sessions[(code, _day(get(cells, "TARIH")))].append((int(prices._num(get(cells, "SEANS NO")) or 0), cells))
    for (code, day), group in sorted(sessions.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        traded = sorted((s, c) for s, c in group if prices._num(get(c, "FIYAT ENDEKSI KAPANIS DEGERI")))
        if not traded:
            continue
        last = traded[-1][1]
        lows = [v for v in (prices._num(get(c, "FIYAT ENDEKSI MINIMUM DEGERI")) for _, c in traded) if v]
        highs = [v for v in (prices._num(get(c, "FIYAT ENDEKSI MAXIMUM DEGERI")) for _, c in traded) if v]
        close = prices._num(get(last, "FIYAT ENDEKSI KAPANIS DEGERI"))
        result.rows.append(Row(
            code, day, _scale(day, close), _scale(day, min(lows) if lows else close),
            _scale(day, max(highs) if highs else close),
            _scale(day, prices._num(get(last, "GETIRI ENDEKSI KAPANIS DEGERI")) or None),
            _lira(day, sum(prices._num(get(c, "ISLEM HACMI")) or 0.0 for _, c in group)),
        ))
    return result


def _schema(conn) -> None:
    conn.execute("""CREATE TABLE IF NOT EXISTS official_indices (
        code TEXT NOT NULL, date TEXT NOT NULL, close REAL NOT NULL, low REAL NOT NULL, high REAL NOT NULL,
        return_close REAL, value REAL NOT NULL, file TEXT NOT NULL, PRIMARY KEY (code, date))""")


def _wanted(path: Path) -> bool:
    name = path.name.upper()
    return name.startswith(("PP_GUNSONUENDEKS", "BISTECH_ONCESI_PP_GUNSONUENDEKS")) and path.suffix.lower() in (
        ".csv", ".txt")


def import_folder(folder: Path | None = None, db: Path | None = None) -> prices.ImportResult:
    """Read the month folders' index files not read before; store the kept indices."""

    folder = Path(folder or INBOX)
    result = prices.ImportResult()
    if not folder.exists():
        return result
    with prices._connect(db) as conn:
        _schema(conn)
        done = {n: (s, m) for n, s, m in conn.execute("SELECT name, size, mtime_ns FROM official_files")}
        files = sorted((p for p in folder.glob("*/*") if p.is_file() and _wanted(p)),
                       key=lambda p: (p.parent.name, 0 if p.name.upper().startswith("BISTECH") else 1))
        for path in files:
            key = f"endeks/{path.parent.name}/{path.name}"
            stat = path.stat()
            if done.get(key) == (stat.st_size, stat.st_mtime_ns):
                continue
            got = read_file(path)
            result.files += 1
            if got.rejected:
                result.rejected.append(f"{key}: {got.rejected}")
                logger.warning("Official index file rejected | %s | %s", key, got.rejected)
            else:
                conn.executemany("INSERT OR REPLACE INTO official_indices VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                 [(r.code, r.day.isoformat(), r.close, r.low, r.high, r.return_close, r.value, key)
                                  for r in got.rows])
                result.rows += len(got.rows)
            conn.execute("INSERT OR REPLACE INTO official_files VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                         (key, stat.st_size, stat.st_mtime_ns, "endeks", len(got.rows),
                          "reddedildi" if got.rejected else "okundu", got.rejected,
                          datetime.now().isoformat(timespec="seconds")))
            conn.commit()
    logger.info("Official indices imported | files %s rows %s rejected %s", result.files, result.rows,
                len(result.rejected))
    return result


def series(code: str = "XU100", start: date | None = None, end: date | None = None, column: str = "close",
           db: Path | None = None) -> pd.Series:
    if column not in ("close", "return_close", "low", "high", "value"):
        raise ValueError(column)
    with prices._connect(db) as conn:
        _schema(conn)
        query = f"SELECT date, {column} FROM official_indices WHERE code = ?"
        params: list = [code]
        if start:
            query += " AND date >= ?"
            params.append(start.isoformat())
        if end:
            query += " AND date <= ?"
            params.append(end.isoformat())
        rows = conn.execute(query + " ORDER BY date", params).fetchall()
    return pd.Series([r[1] for r in rows], index=pd.to_datetime([r[0] for r in rows]), dtype=float, name=code)


def main(argv: list[str] | None = None) -> int:
    """python -m core.official.indices   read the new month folders in data/inbox/bist_endeks"""

    from core.infrastructure.console import utf8_output

    utf8_output()
    got = import_folder()
    print(f"{got.files} yeni endeks dosyası, {got.rows} endeks-gün")
    for line in got.rejected:
        print("REDDEDİLDİ", line)
    return 1 if got.rejected else 0


if __name__ == "__main__":
    raise SystemExit(main())
