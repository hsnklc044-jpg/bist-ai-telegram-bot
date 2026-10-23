"""
QuantBIST
BIST session clock.

Borsa Istanbul's continuous session ends at 18:00 and the closing
auction finishes a few minutes later. A daily candle is treated as
final only after SESSION_FINAL (18:15 Istanbul time). Before that,
today's candle is still moving and must not feed signals.

Holidays are not hard-coded: the trading days are whatever days the
benchmark index (XU100) has candles for.
"""

from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import pandas as pd

ISTANBUL = ZoneInfo("Europe/Istanbul")
SESSION_FINAL = time(18, 15)


def now_istanbul() -> datetime:
    return datetime.now(ISTANBUL)


def last_final_session_date(now: datetime | None = None) -> date:
    """
    The most recent calendar date whose daily candle is final.

    Weekends roll back to Friday. Holidays are not known here; a
    holiday simply has no candle, so nothing needs to be dropped.
    """

    now = (now or now_istanbul()).astimezone(ISTANBUL)
    day = now.date()

    if now.time() < SESSION_FINAL:
        day = (pd.Timestamp(day) - pd.Timedelta(days=1)).date()

    while day.weekday() >= 5:
        day = (pd.Timestamp(day) - pd.Timedelta(days=1)).date()

    return day


def drop_open_candle(
    df: pd.DataFrame,
    now: datetime | None = None,
) -> pd.DataFrame:
    """Remove candles that are not final yet."""

    if df.empty:
        return df

    cutoff = pd.Timestamp(last_final_session_date(now))

    return df[df.index.normalize() <= cutoff]


__all__ = [
    "ISTANBUL",
    "SESSION_FINAL",
    "now_istanbul",
    "last_final_session_date",
    "drop_open_candle",
]
