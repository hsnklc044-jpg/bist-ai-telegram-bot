"""
QuantBIST
One limit rule for every module (DECISIONS K-75).

Borsa İstanbul's daily price limit is ±10%; a move of LIMIT_MOVE (9.5%) or more counts as a limit
move (the last tick before the limit can be a little under 10%). The comparison carries a small
tolerance: 109,5 / 100 − 1 is 0.09499999... in floating point and used to fall on the wrong side in
some modules and not in others.

    limit_up(change)    change >= +9.5%   (an entry at such an open does not fill)
    limit_down(change)  change <= −9.5%
    limit_move(change)  either side
Each works on a float, a numpy array or a pandas Series.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

LIMIT_MOVE = 0.095
TOLERANCE = 1e-9
EDGE = LIMIT_MOVE - TOLERANCE


def limit_up(change):
    """Works as the plain comparison does: a float gives a bool, an array or a Series the same shape."""

    return change >= EDGE


def limit_down(change):
    return change <= -EDGE


def limit_move(change):
    return abs(change) >= EDGE


def _locked(df, side) -> np.ndarray:
    """Per session day (M32 re-validation Y1): a day is locked when all its candles so far show one price
    and its last close is a limit move from the previous day's last close; every candle of that day is
    marked. A daily frame has one candle per day, so this is the plain row rule; an hourly frame no
    longer marks only the first hour of a locked day."""

    high, low, close = (df[k].to_numpy(dtype=float) for k in ("high", "low", "close"))
    if not len(close):
        return np.zeros(0, dtype=bool)
    idx = pd.DatetimeIndex(df.index)
    if idx.tz is not None:
        idx = idx.tz_convert("Europe/Istanbul").tz_localize(None)
    days = idx.normalize().to_numpy()
    starts = np.r_[True, days[1:] != days[:-1]]
    group = np.cumsum(starts) - 1
    n = int(group[-1]) + 1
    top, bottom = np.full(n, -np.inf), np.full(n, np.inf)
    np.maximum.at(top, group, high)
    np.minimum.at(bottom, group, low)
    last = np.r_[np.flatnonzero(starts)[1:] - 1, len(close) - 1]
    day_close = close[last]
    with np.errstate(invalid="ignore", divide="ignore"):
        change = day_close / np.r_[np.nan, day_close[:-1]] - 1
        return ((top <= bottom) & side(change))[group]


def locked_down(df) -> np.ndarray:
    """Days locked at the lower limit (one price all day, −9.5% or more): a sell does not fill."""

    return _locked(df, limit_down)


def locked_up(df) -> np.ndarray:
    """Days locked at the upper limit (one price all day, +9.5% or more): a buy does not fill."""

    return _locked(df, limit_up)


__all__ = ["LIMIT_MOVE", "TOLERANCE", "limit_down", "limit_move", "limit_up", "locked_down", "locked_up"]
