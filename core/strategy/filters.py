"""
QuantBIST
Tradability filters.

Point-in-time screens (each day uses only data up to that day) that
keep a strategy away from thin and speculative stocks:

- liquidity_top     keep the N most traded stocks by 60-day median
                    turnover (close x volume, TL). Rank based, so it
                    does not drift with inflation.
- max_run_up        drop stocks whose 126-day return exceeds this
                    (e.g. 1.0 = +100%). Parabolic run-ups on BIST often
                    end in limit-down series that cannot be exited.
- max_locks         drop stocks with more than this many locked limit
                    days (high == low, |move| >= 9.5%) in 60 sessions.
"""

from __future__ import annotations

import pandas as pd

LIMIT_MOVE = 0.095


def _panel(frames: dict[str, pd.DataFrame], fn) -> pd.DataFrame:
    return pd.concat({s: fn(df) for s, df in frames.items() if not df.empty}, axis=1, sort=True)


def eligibility(
    frames: dict[str, pd.DataFrame],
    liquidity_top: int | None = None,
    liquidity_window: int = 60,
    max_run_up: float | None = None,
    run_up_window: int = 126,
    max_locks: int | None = None,
    lock_window: int = 60,
) -> pd.DataFrame:
    """Boolean panel (dates x symbols): True = tradable that day."""

    ok = _panel(frames, lambda d: d["close"].notna())

    if liquidity_top is not None:
        turnover = _panel(
            frames,
            lambda d: (d["close"] * d["volume"].where(d["volume"] > 0)).rolling(
                liquidity_window, min_periods=liquidity_window // 2
            ).median(),
        )
        ranks = turnover.rank(axis=1, ascending=False)
        ok &= ranks <= liquidity_top

    if max_run_up is not None:
        run_up = _panel(frames, lambda d: d["close"] / d["close"].shift(run_up_window) - 1)
        ok &= ~(run_up > max_run_up)

    if max_locks is not None:

        def locks(d):
            change = d["close"].pct_change()
            flat = d["high"] <= d["low"]
            hit = flat & (change.abs() >= LIMIT_MOVE)
            return hit.astype(int).rolling(lock_window, min_periods=1).sum()

        ok &= _panel(frames, locks) <= max_locks

    return ok.fillna(False).astype(bool)


def apply_eligibility(
    signals: dict[str, pd.DataFrame],
    eligible: pd.DataFrame,
    exit_when_ineligible: bool = False,
) -> dict[str, pd.DataFrame]:
    """Block entries into ineligible stocks (and optionally force exits)."""

    result = {}
    for symbol, sig in signals.items():
        if symbol not in eligible.columns:
            result[symbol] = sig.assign(enter=False)
            continue
        ok = eligible[symbol].reindex(sig.index).fillna(False).astype(bool)
        out = sig.assign(enter=sig["enter"] & ok)
        if exit_when_ineligible:
            out = out.assign(exit=out["exit"] | ~ok)
        result[symbol] = out

    return result


__all__ = [
    "eligibility",
    "apply_eligibility",
]
