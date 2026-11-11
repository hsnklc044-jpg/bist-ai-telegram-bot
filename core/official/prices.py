"""Borsa İstanbul official end-of-day prices and volumes (K, the user's 11.11.2026 decision; level 1, K-82).

The user downloads DataStore's monthly "Gün Sonu Fiyat ve İşlem Hacmi" files (PP_GUNSONUFIYATHACIM.M.YYYYMM.csv,
0 TL, personal use only) into data/inbox/bist. This module only reads them; the files are never changed, moved or
deleted, and they never reach git or the daily backup (they can be downloaded again).

Formats (found on 11.11.2026 by reading the headers of all 467 files, 01.1988–10.2026):
- old system, until 13.11.2015: one row per session (SEANS NO), stock in PAY KODU with SERI KODU "E" for an
  ordinary share, dates 02.06.2008, decimals with a comma or a point; no opening price (only the opening
  session's price in later files); BSIT100 ENDEKS is "E"/"H" in later files and empty in early ones.
- new system (BISTECH) from 16.11.2015: two header lines (Turkish, English), ISLEM  KODU like THYAO.E, dates
  2022-01-31, decimal point; until 09.2019 with the midday session columns, from 10.2019 without.
- November 2015 comes in two files (BISTECH_Oncesi_... and the new one); both are read, a day in both is reported.
Headers are matched by name; a header that is not in the known list, or a missing field, rejects the file with
the reason. Before 1 January 2005: price ÷ 1 000, share count ÷ 1 000, lira value ÷ 1 000 000 (K-84; see OLD_PRICE).
The BIST 100 flag (BSIT100 ENDEKS, "E"/"H") is filled in the old files from 2001; BIST 30 only from 16.11.2015.

The result goes to data/official.db (ordinary shares, the needed columns only); market.db is not touched. The heavy
first fill runs at night (IMPORT_AT), never at bot start or during the 18:00–20:00 report window."""

from __future__ import annotations

import re
import sqlite3
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date, datetime, time
from pathlib import Path

from core.config.paths import DATA_DIR
from core.infrastructure.logger import get_logger

logger = get_logger(__name__)

INBOX = DATA_DIR / "inbox" / "bist"
OFFICIAL_DB = DATA_DIR / "official.db"
IMPORT_AT = time(2, 30)  # nightly: only files not read before
OLD_LIRA_UNTIL = date(2005, 1, 1)  # the six zeros were dropped on 1 January 2005
# Before 2005 the files quote the old share (1 000 TL nominal) in old lira. On 1 January 2005 the lira lost six
# zeros and 1 000 old shares became one share, so a price is divided by 1 000, a share count by 1 000 and a lira
# value by 1 000 000 (K-84). Checked on 11.11.2026 on all files: with prices ÷ 1 000 000 (as first written in the
# request) 297 shares jumped 1 000-fold on 03.01.2005 (THYAO 29.12.2004 7950 → 03.01.2005 7,85, whose own
# "previous close" is 7,95); with ÷ 1 000 none did, and value / quantity / close stays ~1,00 in every year.
OLD_PRICE = 1_000
OLD_QUANTITY = 1_000
OLD_LIRA = 1_000_000


def _norm(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().upper())


_OLD_FIELDS = (
    "TARIH;SEANS NO;PAZAR;PAY KODU;SERI KODU;MIN FIYAT;MAX FIYAT;ONCEKI KAPANIS FIYAT;KAPANIS FIYAT;AOF;ISLEM HACMI;"
    "ISLEM MIKTARI;SOZLESME SAYISI;SEANS SIRA NO;BAZ FIYAT;ALT LIMIT;UST LIMIT;MAX LOT;REFERANS FIYAT;BSIT100 ENDEKS;"
    "ACILIS SEANSI FIYAT;ACILIS SEANSI ISLEM MIKTARI;ACILIS SEANSI SOZLESME SAYISI;GAOF;GRUP;BRUT TAKAS;"
    "PIYASA YAPICI KOD;ISLEM YONTEMI;KAPANIS SEANSI ISLEM MIKTARI;KAPANIS SEANSI ISLEM HACMI;TEK FIYAT ISLEM MIKTARI;"
    "TEK FIYAT SOZLESME SAYISI;KAPANIS SEANSI FIYATI;EN IYI ALIS FIYATI;EN IYI SATIS FIYATI"
)
_NEW_FIELDS = (
    "TARIH;ISLEM KODU;BULTEN ADI;A_B_C_D GRUBU;PAZAR GRUBU;PAZAR;YAPISAL BAZDA PIYASA ALT BOLUMU;ENSTRUMAN GRUBU;"
    "ENSTRUMAN TIPI;ENSTRUMAN SINIFI;ISLEM YONTEMI;PIYASA YAPICI;BIST 100 ENDEKS;BIST 30 ENDEKS;BRUT TAKAS;"
    "OZSERMAYE HALI;GECICI DURDURMA;ONCEKI KAPANIS FIYATI;ACILIS FIYATI;ACILIS SEANSI FIYATI;GUNORTASI SEANSI FIYATI;"
    "EN DUSUK FIYAT;EN YUKSEK FIYAT;KAPANIS FIYATI;KAPANIS SEANSI FIYATI;DEGISIM (%);BEKLEYEN EN IYI ALIS;"
    "BEKLEYEN EN IYI SATIS;A.O.F;TOPLAM ISLEM HACMI;TOPLAM ISLEM ADEDI;TOPLAM SOZLESME SAYISI;REFERANS FIYAT;"
    "ACILIS SEANSI ISLEM HACMI;ACILIS SEANSI ISLEM MIKTARI;ACILIS SEANSI SOZLESME SAYISI;"
    "GUNORTASI MUZAYEDE ISLEM HACMI;GUNORTASI MUZAYEDE ISLEM MIKTARI;GUNORTASI MUZAYEDE SOZLESME SAYISI;"
    "KAPANIS SEANSI ISLEM HACMI;KAPANIS SEANSI ISLEM MIKTARI;KAPANIS SEANSI SOZLESME SAYISI;"
    "KAPANIS FIYATINDAN ISLEMLER ISLEM HACMI;KAPANIS FIYATINDAN ISLEMLER ISLEM MIKTARI;"
    "KAPANIS FIYATINDAN ISLEMLER SOZLESME SAYISI;EN DUSUK ACIGA SATIS FIYATI;EN YUKSEK ACIGA SATIS FIYATI;"
    "ACIGA SATIS A.O.F;ACIGA SATIS ISLEM HACMI;ACIGA SATIS ISLEM ADEDI;ACIGA SATIS SOZLESME SAYISI;"
    "OZEL ISLEM BILDIRIMI EN DUSUK FIYAT;OZEL ISLEM BILDIRIMI EN YUKSEK FIYAT;OZEL ISLEM BILDIRIMI A.O.F.;"
    "OZEL ISLEM BILDIRIMI ISLEM HACMI;OZEL ISLEM BILDIRIMI ISLEM ADEDI;OZEL ISLEM BILDIRIMI SOZLESME SAYISI"
)
KNOWN = {"eski": frozenset(_OLD_FIELDS.split(";")), "yeni": frozenset(_NEW_FIELDS.split(";"))}
REQUIRED = {
    "eski": ("TARIH", "SEANS NO", "PAY KODU", "SERI KODU", "MIN FIYAT", "MAX FIYAT", "ONCEKI KAPANIS FIYAT",
             "KAPANIS FIYAT", "ISLEM HACMI", "ISLEM MIKTARI"),
    "yeni": ("TARIH", "ISLEM KODU", "ACILIS FIYATI", "EN YUKSEK FIYAT", "EN DUSUK FIYAT", "KAPANIS FIYATI",
             "TOPLAM ISLEM HACMI", "TOPLAM ISLEM ADEDI", "ONCEKI KAPANIS FIYATI", "BIST 100 ENDEKS",
             "BIST 30 ENDEKS"),
}


@dataclass(frozen=True)
class Row:
    code: str
    day: date
    open: float | None
    high: float
    low: float
    close: float
    prev_close: float | None
    value: float  # TL traded
    quantity: float  # shares traded
    bist100: int | None  # the day's membership flag; None = not in the file
    bist30: int | None


@dataclass
class FileResult:
    name: str
    system: str | None = None
    rows: list[Row] = field(default_factory=list)
    rejected: str | None = None


def _decode(raw: bytes) -> str:
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16")
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("cp1254")  # Latin-5, some older files


def _num(text: str) -> float | None:
    text = text.strip()
    if not text:
        return None
    if "," in text and "." not in text:
        text = text.replace(",", ".")  # old files: decimal comma
    try:
        return float(text)
    except ValueError:
        return None


def _day(text: str) -> date:
    text = text.strip()
    if "-" in text:
        return date.fromisoformat(text)
    return datetime.strptime(text, "%d.%m.%Y").date()


def _flag(text: str) -> int | None:
    text = text.strip().upper()
    if text in ("1", "E"):
        return 1
    if text in ("0", "H"):
        return 0
    return None


def _system(header: list[str]) -> tuple[str | None, str | None]:
    names = set(header)
    system = "yeni" if "ISLEM KODU" in names else "eski" if "PAY KODU" in names else None
    if system is None:
        return None, "bilinmeyen biçim: ne ISLEM KODU ne PAY KODU başlığı var"
    unknown = [h for h in header if h and h not in KNOWN[system]]
    if unknown:
        return None, f"bilinmeyen başlık ({system} sistem): {', '.join(unknown)}"
    missing = [h for h in REQUIRED[system] if h not in names]
    if missing:
        return None, f"eksik alan ({system} sistem): {', '.join(missing)}"
    return system, None


def _old(value: float | None, day: date, divisor: int) -> float | None:
    return None if value is None else value / divisor if day < OLD_LIRA_UNTIL else value


def read_file(path: Path) -> FileResult:
    path = Path(path)
    result = FileResult(path.name)
    lines = _decode(path.read_bytes()).splitlines()
    if not lines:
        result.rejected = "boş dosya"
        return result
    header = [_norm(h) for h in lines[0].split(";")]
    system, why = _system(header)
    if system is None:
        result.rejected = why
        return result
    result.system = system
    col = {h: i for i, h in enumerate(header)}
    body = [line.split(";") for line in lines[1:] if line.strip()]
    body = [c for c in body if not c[0].strip().upper().startswith(("TRADE DATE", "DATE"))]  # the English header

    def get(cells, name):
        i = col.get(name)
        return cells[i] if i is not None and i < len(cells) else ""

    if system == "yeni":
        for cells in body:
            code = get(cells, "ISLEM KODU").strip()
            if not code.endswith(".E"):
                continue  # warrants (.V), certificates, funds and the rest
            day = _day(get(cells, "TARIH"))
            close = _num(get(cells, "KAPANIS FIYATI"))
            if not close:
                continue  # no trade that day
            result.rows.append(Row(
                code=code[:-2], day=day, open=_num(get(cells, "ACILIS FIYATI")) or None,
                high=_num(get(cells, "EN YUKSEK FIYAT")) or close, low=_num(get(cells, "EN DUSUK FIYAT")) or close,
                close=close, prev_close=_num(get(cells, "ONCEKI KAPANIS FIYATI")) or None,
                value=_num(get(cells, "TOPLAM ISLEM HACMI")) or 0.0,
                quantity=_num(get(cells, "TOPLAM ISLEM ADEDI")) or 0.0,
                bist100=_flag(get(cells, "BIST 100 ENDEKS")), bist30=_flag(get(cells, "BIST 30 ENDEKS")),
            ))
        return result

    sessions: dict[tuple[str, date], list[tuple[int, list[str]]]] = defaultdict(list)
    for cells in body:
        if get(cells, "SERI KODU").strip().upper() != "E":
            continue
        code = get(cells, "PAY KODU").strip()
        if not code:
            continue
        session = int(_num(get(cells, "SEANS NO")) or 0)
        sessions[(code, _day(get(cells, "TARIH")))].append((session, cells))
    for (code, day), group in sorted(sessions.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        group.sort(key=lambda s: s[0])
        traded = [(s, c) for s, c in group if _num(get(c, "KAPANIS FIYAT"))]
        if not traded:
            continue
        last = traded[-1][1]
        first = group[0][1]
        highs = [v for v in (_num(get(c, "MAX FIYAT")) for _, c in traded) if v]
        lows = [v for v in (_num(get(c, "MIN FIYAT")) for _, c in traded) if v]
        close = _num(get(last, "KAPANIS FIYAT"))
        opening = _num(get(first, "ACILIS SEANSI FIYAT")) or None
        p = OLD_PRICE
        result.rows.append(Row(
            code=code, day=day,
            open=_old(opening, day, p),
            high=_old(max(highs) if highs else close, day, p), low=_old(min(lows) if lows else close, day, p),
            close=_old(close, day, p), prev_close=_old(_num(get(first, "ONCEKI KAPANIS FIYAT")) or None, day, p),
            value=_old(sum(_num(get(c, "ISLEM HACMI")) or 0.0 for _, c in group), day, OLD_LIRA),
            quantity=_old(sum(_num(get(c, "ISLEM MIKTARI")) or 0.0 for _, c in group), day, OLD_QUANTITY),
            bist100=_flag(get(first, "BSIT100 ENDEKS")), bist30=None,
        ))
    return result


# --- data/official.db ---------------------------------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS official_prices (
    code TEXT NOT NULL, date TEXT NOT NULL,
    open REAL, high REAL NOT NULL, low REAL NOT NULL, close REAL NOT NULL, prev_close REAL,
    value REAL NOT NULL, quantity REAL NOT NULL, bist100 INTEGER, bist30 INTEGER, file TEXT NOT NULL,
    PRIMARY KEY (code, date)
);
CREATE TABLE IF NOT EXISTS official_files (
    name TEXT PRIMARY KEY, size INTEGER NOT NULL, mtime_ns INTEGER NOT NULL, system TEXT, rows INTEGER NOT NULL,
    status TEXT NOT NULL, reason TEXT, read_at TEXT NOT NULL
);
"""


@contextmanager
def _connect(path: Path | None = None):
    path = Path(path or OFFICIAL_DB)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    try:
        conn.executescript(_SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


@dataclass
class ImportResult:
    files: int = 0  # files read this time
    rows: int = 0  # share-days read
    rejected: list[str] = field(default_factory=list)  # "name: reason"
    overlaps: list[tuple[str, date]] = field(default_factory=list)  # the same share-day in two files


def _order(path: Path) -> tuple[str, int]:
    month = re.search(r"(\d{6})", path.name)
    # the old half of November 2015 first, so the new system's row stands when a day is in both
    return (month.group(1) if month else path.name, 0 if path.name.upper().startswith("BISTECH") else 1)


def import_folder(folder: Path | None = None, db: Path | None = None) -> ImportResult:
    """Read the files not read before (name, size and modification time); store ordinary shares' days."""

    folder = Path(folder or INBOX)
    result = ImportResult()
    if not folder.exists():
        return result
    with _connect(db) as conn:
        done = {name: (size, mtime) for name, size, mtime in
                conn.execute("SELECT name, size, mtime_ns FROM official_files")}
        for path in sorted(folder.glob("*.csv"), key=_order):
            stat = path.stat()
            if done.get(path.name) == (stat.st_size, stat.st_mtime_ns):
                continue
            got = read_file(path)
            result.files += 1
            stamp = datetime.now().isoformat(timespec="seconds")
            if got.rejected:
                result.rejected.append(f"{path.name}: {got.rejected}")
                logger.warning("Official price file rejected | %s | %s", path.name, got.rejected)
            else:
                days = {(r.code, r.day.isoformat()) for r in got.rows}
                if days:
                    seen = {}
                    for code, day in days:
                        seen.setdefault(day, []).append(code)
                    for day, codes in seen.items():
                        q = ",".join("?" * len(codes))
                        for (code, other) in conn.execute(
                                f"SELECT code, file FROM official_prices WHERE date = ? AND code IN ({q})",
                                (day, *codes)):
                            if other != path.name:
                                result.overlaps.append((code, date.fromisoformat(day)))
                conn.executemany(
                    "INSERT OR REPLACE INTO official_prices VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [(r.code, r.day.isoformat(), r.open, r.high, r.low, r.close, r.prev_close, r.value,
                      r.quantity, r.bist100, r.bist30, path.name) for r in got.rows])
                result.rows += len(got.rows)
            conn.execute("INSERT OR REPLACE INTO official_files VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                         (path.name, stat.st_size, stat.st_mtime_ns, got.system, len(got.rows),
                          "reddedildi" if got.rejected else "okundu", got.rejected, stamp))
            conn.commit()
    result.overlaps.sort(key=lambda x: (x[1], x[0]))
    if result.overlaps:
        logger.warning("Official prices: a share-day in two files | %s", result.overlaps[:20])
    logger.info("Official prices imported | files %s rows %s rejected %s", result.files, result.rows,
                len(result.rejected))
    return result


def members(day: date, index: str = "bist100", db: Path | None = None) -> set[str]:
    """The shares flagged as members of BIST 100 (or BIST 30) on `day` in the official file."""

    column = {"bist100": "bist100", "bist30": "bist30"}[index]
    with _connect(db) as conn:
        rows = conn.execute(f"SELECT code FROM official_prices WHERE date = ? AND {column} = 1", (day.isoformat(),))
        return {r[0] for r in rows}


def main(argv: list[str] | None = None) -> int:
    """python -m core.official.prices          read the new files in data/inbox/bist into data/official.db
       python -m core.official.prices --durum  what has been read"""

    import argparse

    from core.infrastructure.console import utf8_output

    utf8_output()
    parser = argparse.ArgumentParser(description="Borsa İstanbul resmî gün sonu fiyatları")
    parser.add_argument("--durum", action="store_true")
    args = parser.parse_args(argv)
    if args.durum:
        with _connect() as conn:
            files, rows, rejected = conn.execute(
                "SELECT COUNT(*), COALESCE(SUM(rows), 0), SUM(status = 'reddedildi') FROM official_files").fetchone()
            first, last, shares = conn.execute(
                "SELECT MIN(date), MAX(date), COUNT(DISTINCT code) FROM official_prices").fetchone()
        print(f"{files} dosya okundu ({rejected or 0} reddedildi), {rows} hisse-gün, {shares} hisse, {first} – {last}")
        return 0
    got = import_folder()
    print(f"{got.files} yeni dosya, {got.rows} hisse-gün")
    for line in got.rejected:
        print("REDDEDİLDİ", line)
    for code, day in got.overlaps[:50]:
        print(f"İKİ DOSYADA: {code} {day:%d.%m.%Y}")
    return 1 if got.rejected else 0


if __name__ == "__main__":
    raise SystemExit(main())
