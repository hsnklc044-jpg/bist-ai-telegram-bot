"""
QuantBIST
The filter record (owner's instruction #15): every morning table's rows are appended to
data/filtre_kayitlari.csv (append-only, once per day per stock; past rows are never rewritten). The
reference is the last stored close before the message.

When 20 trading days (counted on the stored XU100.IS days after the reference day) have passed, the
weekday 19:15 job appends the record's outcome to a SEPARATE file, data/filtre_sonuclari.csv (append-only,
written once per record, the same pattern as core.research.tahmin_defteri daily()/RESULTS):

- nominal: close on the 20th trading day / reference close - 1;
- XU100-relative: nominal minus XU100.IS's return over the same two days (percentage points);
- USD: macro.usd_return (both legs at the TCMB rate of their day);
- real: macro.real_return (TÜFE, months after the last published one are never estimated).

Missing data leaves the field empty; nothing is guessed. A stock with no close on the 20th session (halted,
or the store is behind) is tried again on later evenings; after 10 more XU100 sessions its row is written with
empty returns and "veri yok" in the `not` column (final). The record file holds the record only; files written
before this rule keep their four always-empty sonuc_* columns and are still read and appended to. This is a record, not a test: no statistics and
no hit rates are computed here. Both files are personal (not in git).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date

import pandas as pd

from core.config.paths import DATA_DIR
from core.infrastructure.csvfiles import open_append
from core.infrastructure.logger import get_logger

logger = get_logger(__name__)

RECORDS = DATA_DIR / "filtre_kayitlari.csv"
RESULTS = DATA_DIR / "filtre_sonuclari.csv"
RECORD_COLUMNS = ("kayit_tarihi", "hisse", "filtreler", "referans_tarihi", "referans_kapanis")
OLD_RECORD_COLUMNS = (*RECORD_COLUMNS, "sonuc_nominal", "sonuc_xu100_goreli", "sonuc_usd", "sonuc_reel")
RESULT_COLUMNS = ("kayit_tarihi", "hisse", "referans_tarihi", "bitis_tarihi", "nominal_yuzde",
                  "xu100_goreli_yuzde", "usd_yuzde", "reel_yuzde", "isaretlendi", "not")
SESSIONS = 20
GRACE = 10  # more XU100 sessions to wait for a missing 20th-session close before the result is final
NO_DATA = "veri yok"
BENCH = "XU100.IS"


@dataclass(frozen=True)
class Record:
    code: str  # "GARAN" (no .IS)
    screens: list[str]
    ref_day: date
    ref_close: float


def _read(path) -> list[dict]:
    from pathlib import Path

    path = Path(path)
    if not path.exists():
        return []
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _header(path) -> tuple[str, ...]:
    from pathlib import Path

    path = Path(path)
    if not path.exists() or not path.stat().st_size:
        return ()
    with open(path, encoding="utf-8", newline="") as fh:
        return tuple(next(csv.reader(fh), ()))


def append_records(records: list[Record], day: date, path=None) -> int:
    """Append today's rows; a stock already recorded today is skipped. Returns the number written. A file in
    the old layout (OLD_RECORD_COLUMNS) gets its empty columns, so its rows stay aligned."""

    path = path or RECORDS
    done = {(r.get("kayit_tarihi"), r.get("hisse")) for r in _read(path)}
    new = [r for r in records if (day.isoformat(), r.code) not in done]
    if not new:
        return 0
    pad = [""] * (len(OLD_RECORD_COLUMNS) - len(RECORD_COLUMNS)) if _header(path) == OLD_RECORD_COLUMNS else []
    fh, new_file = open_append(path)
    with fh:
        out = csv.writer(fh, lineterminator="\n")
        if new_file:
            out.writerow(RECORD_COLUMNS)
        for r in new:
            out.writerow([day.isoformat(), r.code, ";".join(r.screens), r.ref_day.isoformat(),
                          f"{r.ref_close:.6g}", *pad])
    return len(new)


def _days(df: pd.DataFrame) -> pd.Series:
    s = df["close"].dropna().copy()
    s.index = pd.to_datetime(s.index)
    if s.index.tz is not None:
        s.index = s.index.tz_convert("Europe/Istanbul").tz_localize(None)
    s.index = s.index.normalize()
    return s.sort_index()


def _close_on(s: pd.Series | None, day: pd.Timestamp) -> float | None:
    if s is None or day not in s.index:
        return None
    value = float(s.loc[day])
    return value if value > 0 else None


def _num(value: float | None) -> str:
    return "" if value is None else f"{100 * value:.4f}"


def outcome(row: dict, bench: pd.Series, read, usd, cpi, today: date) -> dict | None:
    """The results row of a due record; None while its 20 trading days have not passed, and None while the
    stock has no close on the 20th session until GRACE more XU100 sessions have passed: then the row is written
    with empty returns and "veri yok" in `not` (final)."""

    from core.market import macro

    ref = date.fromisoformat(row["referans_tarihi"])
    ref_close = float(row["referans_kapanis"])
    after = bench.index[bench.index.date > ref]
    if len(after) < SESSIONS or after[SESSIONS - 1].date() > today:
        return None
    end = after[SESSIONS - 1]
    try:
        stock = _days(read(f"{row['hisse']}.IS"))
    except KeyError:
        stock = None
    end_close = _close_on(stock, end)
    if end_close is None and (len(after) < SESSIONS + GRACE or after[SESSIONS + GRACE - 1].date() > today):
        return None  # tried again on a later evening
    nominal = end_close / ref_close - 1 if end_close is not None and ref_close > 0 else None
    relative = usd_value = real = None
    if nominal is not None:
        a, b = _close_on(bench, pd.Timestamp(ref)), _close_on(bench, end)
        relative = nominal - (b / a - 1) if a is not None and b is not None else None
        usd_value = macro.usd_return(nominal, ref, end.date(), usd) if usd is not None and len(usd) else None
        real = macro.real_return(nominal, ref, end.date(), cpi) if cpi is not None and len(cpi) else None
    return {"kayit_tarihi": row["kayit_tarihi"], "hisse": row["hisse"], "referans_tarihi": ref.isoformat(),
            "bitis_tarihi": end.date().isoformat(), "nominal_yuzde": _num(nominal),
            "xu100_goreli_yuzde": _num(relative), "usd_yuzde": _num(usd_value), "reel_yuzde": _num(real),
            "isaretlendi": today.isoformat(), "not": "" if nominal is not None else NO_DATA}


def _store_read(symbol: str) -> pd.DataFrame:
    from core.market import store

    return store.read(symbol)


def fill_results(today: date, records=None, results=None, read=None, usd=None, cpi=None) -> list[str]:
    """Append the outcome of every record whose 20 trading days have passed and that has no result yet.
    One line per new result (for the log). A bad record is skipped and logged; never raises for one."""

    from core.market import macro

    records, results, read = records or RECORDS, results or RESULTS, read or _store_read
    rows = _read(records)
    if not rows:
        return []
    done = {(r.get("kayit_tarihi"), r.get("hisse")) for r in _read(results)}
    todo = [r for r in rows if (r.get("kayit_tarihi"), r.get("hisse")) not in done]
    if not todo:
        return []
    bench = _days(read(BENCH))
    usd = macro.load_usdtry() if usd is None else usd
    cpi = macro.load_cpi() if cpi is None else cpi
    new = []
    for row in todo:
        key = (row.get("kayit_tarihi"), row.get("hisse"))
        if key in done:
            continue
        try:
            got = outcome(row, bench, read, usd, cpi, today)
        except Exception as exc:  # noqa: BLE001 - one bad record never stops the others
            logger.warning("Filtre kaydı atlandı: %s %s | %s: %s", *key, type(exc).__name__, exc)
            continue
        if got:
            new.append(got)
            done.add(key)
    if not new:
        return []
    fields = _header(results) or RESULT_COLUMNS  # an older results file keeps its own columns
    fh, new_file = open_append(results)
    with fh:
        out = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        if new_file:
            out.writeheader()
        out.writerows(new)
    return [f"{r['hisse']} ({r['kayit_tarihi']} → {r['bitis_tarihi']}): nominal {r['nominal_yuzde'] or '—'}"
            for r in new]


__all__ = ["GRACE", "NO_DATA", "OLD_RECORD_COLUMNS", "RECORDS", "RECORD_COLUMNS", "RESULTS", "RESULT_COLUMNS", "Record", "append_records", "fill_results",
           "outcome"]
