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


    high, low, close = (df[k].to_numpy(dtype=float) for k in ("high", "low", "close"))
    change = close / np.r_[np.nan, close[:-1]] - 1
    with np.errstate(invalid="ignore"):
        return (high <= low) & side(change)


def locked_down(df) -> np.ndarray:
    """Days locked at the lower limit (one price all day, −9.5% or more): a sell does not fill."""

    return _locked(df, limit_down)


def locked_up(df) -> np.ndarray:
    """Days locked at the upper limit (one price all day, +9.5% or more): a buy does not fill."""

    return _locked(df, limit_up)


__all__ = ["LIMIT_MOVE", "TOLERANCE", "limit_down", "limit_move", "limit_up", "locked_down", "locked_up"]
