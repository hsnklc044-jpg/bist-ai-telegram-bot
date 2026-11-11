"""r2 research frames from the old-system official files, 2001–2015 (K-92; RESEARCH_LOG "r2 ön kaydı").

In these files a day's first session BAZ FIYAT is the previous day's AOF (99.8 % of day transitions, checked on
11.11.2026); a deviation of more than THRESHOLD is the exchange's own corporate action factor (split, rights,
dividend), so the series before that day is scaled by it. Dividends are adjusted too, so the benchmark is the XU100
return index. The latest prices are the traded ones; share counts are scaled the other way, so the lira volume stays
as traded. The files are read directly (core.official.prices.read_file); the database is not changed."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pandas as pd

from core.official import indices, prices

THRESHOLD = 0.005
OLD_SYSTEM_UNTIL = date(2015, 11, 13)


def frame(rows: list) -> pd.DataFrame:
    """One stock's rows (core.official.prices.Row, oldest first) as an adjusted OHLCV frame."""

    rows = sorted(rows, key=lambda r: r.day)
    index = pd.DatetimeIndex([pd.Timestamp(r.day) for r in rows])
    close = pd.Series([r.close for r in rows], index=index, dtype=float)
    r = close.pct_change()
    for i in range(1, len(rows)):
        prev, cur = rows[i - 1], rows[i]
        if cur.base and prev.aof:
            f = cur.base / prev.aof
            if abs(f - 1) > THRESHOLD:
                r.iloc[i] = cur.close / (prev.close * f) - 1
    r.iloc[0] = 0.0
    growth = (1 + r).cumprod()
    adjusted = growth / growth.iloc[-1] * close.iloc[-1]
    factor = adjusted / close
    raw = pd.DataFrame({"open": [r.open if r.open else r.close for r in rows], "high": [r.high for r in rows],
                        "low": [r.low for r in rows], "volume": [r.quantity for r in rows]}, index=index, dtype=float)
    return pd.DataFrame({"open": raw["open"] * factor, "high": raw["high"] * factor, "low": raw["low"] * factor,
                         "close": adjusted, "volume": raw["volume"] / factor})


def load(start: date, end: date, inbox: Path | None = None, db: Path | None = None
         ) -> tuple[dict[str, pd.DataFrame], pd.DataFrame, pd.DataFrame]:
    """(frames, XU100 return-index frame, eligibility) for start..end, both inside the old system."""

    if end > OLD_SYSTEM_UNTIL:
        raise ValueError(f"r2 eski sistem dönemi {OLD_SYSTEM_UNTIL} günü biter; bitiş {end}")
    inbox = Path(inbox or prices.INBOX)
    months = {f"{y}{m:02d}" for y in range(start.year, end.year + 1) for m in range(1, 13)}
    by_code: dict[str, list] = {}
    for path in sorted(inbox.glob("*.csv")):
        month = re.search(r"(\d{6})", path.name)
        if not month or month.group(1) not in months:
            continue
        if month.group(1) == "201511" and not path.name.upper().startswith("BISTECH"):
            continue  # the new-system half of November 2015
        for r in prices.read_file(path).rows:
            if start <= r.day <= end:
                by_code.setdefault(r.code, []).append(r)
    frames = {f"{code}.IS": frame(rows) for code, rows in by_code.items()}
    ret = indices.series("XU100", start, end, column="return_close", db=db).dropna()
    bench = pd.DataFrame({"open": ret, "high": ret, "low": ret, "close": ret, "volume": 0.0})
    flags = {f"{code}.IS": pd.Series([r.bist100 == 1 for r in sorted(rows, key=lambda r: r.day)],
                                     index=pd.DatetimeIndex([pd.Timestamp(r.day) for r in sorted(rows, key=lambda r: r.day)]))
             for code, rows in by_code.items()}
    eligible = pd.DataFrame({s: f.reindex(bench.index).fillna(False).astype(bool) for s, f in flags.items()},
                            index=bench.index)
    return frames, bench, eligible


__all__ = ["OLD_SYSTEM_UNTIL", "THRESHOLD", "frame", "load"]
