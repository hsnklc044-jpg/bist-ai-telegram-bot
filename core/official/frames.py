"""Research price frames from the official data (r1, K-91; RESEARCH_LOG "r1 ön kaydı").

After November 2015 the official files carry no adjustment ratio (REFERANS FIYAT is 0, ONCEKI KAPANIS FIYATI is the
raw previous close). On a day with the exchange's corporate action code 01 (rights), 03 (bonus/split), 04 (capital
reduction), 05 or 99, the stock's return is replaced by XU100's return that day (market-neutral fill); 06 (cash
dividend) stays raw, as XU100 is a price index too. The series before such a day is scaled so the returns are
continuous and the latest prices are the traded ones; share counts are scaled the other way, so the lira volume stays
as traded. The benchmark is the official XU100 (K-86); membership is the official daily BIST 100 flag (K-85). Nothing
on or after HOLDOUT_START is ever loaded."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pandas as pd

from core.official import indices, prices

ADJUSTING = {"01", "03", "04", "05", "99"}
NEW_SYSTEM_FROM = date(2015, 11, 16)  # the first day with the exchange's corporate action code


def is_adjusting(code: str | None) -> bool:
    return isinstance(code, str) and bool(ADJUSTING & set(re.split(r"[&\-, ]+", code.strip())))


def load(start: date, end: date, db: Path | None = None) -> tuple[dict[str, pd.DataFrame], pd.DataFrame, pd.DataFrame]:
    """(frames by "CODE.IS", XU100 frame, eligibility panel) for start..end (both included)."""

    from core.backtest.run import HOLDOUT_START

    start, end = pd.Timestamp(start).date(), pd.Timestamp(end).date()
    if end >= pd.Timestamp(HOLDOUT_START).date():
        raise ValueError(f"holdout kapalı: bitiş {end} ≥ {pd.Timestamp(HOLDOUT_START).date()}")
    start = max(start, NEW_SYSTEM_FROM)
    xu = indices.series("XU100", start, end, db=db)
    lows = indices.series("XU100", start, end, column="low", db=db)
    highs = indices.series("XU100", start, end, column="high", db=db)
    bench = pd.DataFrame({"open": xu, "high": highs, "low": lows, "close": xu, "volume": 0.0})
    xu_ret = xu.pct_change()
    with prices._connect(db) as conn:
        raw = pd.read_sql_query(
            "SELECT code, date, open, high, low, close, quantity, bist100, corp_action FROM official_prices "
            "WHERE date BETWEEN ? AND ? ORDER BY code, date", conn, params=(start.isoformat(), end.isoformat()),
            parse_dates=["date"])
    frames: dict[str, pd.DataFrame] = {}
    flags: dict[str, pd.Series] = {}
    for code, g in raw.groupby("code"):
        g = g.set_index("date").sort_index()
        close = g["close"].astype(float)
        r = close.pct_change()
        fill = g["corp_action"].map(is_adjusting).fillna(False).astype(bool)
        r[fill] = xu_ret.reindex(close.index)[fill].fillna(0.0)
        r.iloc[0] = 0.0
        growth = (1 + r).cumprod()
        adjusted = growth / growth.iloc[-1] * close.iloc[-1]  # the latest price is the traded one
        factor = adjusted / close
        frame = pd.DataFrame({
            "open": g["open"].astype(float).fillna(close) * factor,
            "high": g["high"].astype(float) * factor,
            "low": g["low"].astype(float) * factor,
            "close": adjusted,
            "volume": g["quantity"].astype(float) / factor,  # close × volume stays the traded lira value
        })
        frames[f"{code}.IS"] = frame
        flags[f"{code}.IS"] = g["bist100"].fillna(0).astype(int) == 1
    index = bench.index
    eligible = pd.DataFrame({s: f.reindex(index).fillna(False).astype(bool) for s, f in flags.items()}, index=index)
    return frames, bench, eligible


__all__ = ["ADJUSTING", "NEW_SYSTEM_FROM", "is_adjusting", "load"]
