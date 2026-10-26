"""
QuantBIST
Candidate rules under research (October 2026). None of them is a signal
until it passes the three gates in core.backtest.candidates.

Every value on day t uses only candles up to the close of day t
(tests/test_no_lookahead.py covers these rules too).
"""

from __future__ import annotations

import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator


def _frame(enter, exit_, rank, index) -> pd.DataFrame:
    return pd.DataFrame(
        {"enter": enter.fillna(False).astype(bool), "exit": exit_.fillna(False).astype(bool), "rank": rank.fillna(0.0)},
        index=index,
    )


def breakout_rule(entry_days: int = 55, exit_days: int = 20, volume_multiple: float = 1.5):
    """Close above the highest high of the previous `entry_days` with above-average volume."""

    def rule(df: pd.DataFrame) -> pd.DataFrame:
        high_prev = df["high"].rolling(entry_days).max().shift(1)
        low_prev = df["low"].rolling(exit_days).min().shift(1)
        vol = df["volume"].where(df["volume"] > 0)
        vol_avg = vol.rolling(20, min_periods=10).mean().shift(1)
        enter = (df["close"] > high_prev) & (vol > volume_multiple * vol_avg)
        exit_ = df["close"] < low_prev
        rank = df["close"] / high_prev - 1
        return _frame(enter, exit_, rank, df.index)

    rule.__name__ = f"breakout_{entry_days}_{exit_days}"
    return rule


def weekly_values(series: pd.Series, fn) -> pd.Series:
    """
    Apply `fn` to weekly closes and map back to days. A week's value is used
    from the first trading day AFTER the week, so a half-finished week (live
    data on a Wednesday) is never treated as complete and the backtest and a
    live run agree on every day.
    """

    weekly = series.groupby(series.index.to_period("W-FRI")).agg(["last"])
    last_day = series.index.to_series().groupby(series.index.to_period("W-FRI")).max()
    values = fn(weekly["last"])
    values.index = last_day.values
    return values.reindex(series.index, method="ffill").shift(1)


def weekly_trend_rule(fast: int = 10, slow: int = 30, daily_ema: int = 50):
    """Weekly EMA(fast) > EMA(slow) and weekly close above EMA(slow), with the daily close above EMA(daily)."""

    def rule(df: pd.DataFrame) -> pd.DataFrame:
        close = df["close"]

        def weekly_ok(w: pd.Series) -> pd.Series:
            ef = EMAIndicator(w, window=fast).ema_indicator()
            es = EMAIndicator(w, window=slow).ema_indicator()
            return ((ef > es) & (w > es)).astype(float).where(es.notna())

        weekly = weekly_values(close, weekly_ok) == 1.0
        daily = close > EMAIndicator(close, window=daily_ema).ema_indicator()
        up = weekly & daily
        rank = close / close.shift(63) - 1
        return _frame(up, ~up, rank, df.index)

    rule.__name__ = f"weekly_trend_{fast}_{slow}_{daily_ema}"
    return rule


def dryup_breakout_rule(dry_ratio: float = 0.7, breakout_days: int = 60, volume_multiple: float = 2.0):
    """
    Volume dries up (20-day average below `dry_ratio` x 120-day average at some
    point in the last 20 sessions), then the close breaks the `breakout_days`
    high on `volume_multiple` x the 20-day average volume. Exit below EMA50.
    """

    def rule(df: pd.DataFrame) -> pd.DataFrame:
        vol = df["volume"].where(df["volume"] > 0)
        avg20 = vol.rolling(20, min_periods=15).mean()
        avg120 = vol.rolling(120, min_periods=90).mean()
        dried = (avg20 < dry_ratio * avg120).astype(float).rolling(20, min_periods=1).max() > 0
        high_prev = df["high"].rolling(breakout_days).max().shift(1)
        burst = vol > volume_multiple * avg20.shift(1)
        enter = dried.shift(1).fillna(False).astype(bool) & (df["close"] > high_prev) & burst
        ema50 = EMAIndicator(df["close"], window=50).ema_indicator()
        exit_ = df["close"] < ema50
        rank = vol / avg20.shift(1)
        return _frame(enter, exit_, rank, df.index)

    rule.__name__ = f"dryup_breakout_{dry_ratio:g}_{breakout_days}_{volume_multiple:g}"
    return rule


def grouped_score_rule(enter_at: int = 3, exit_at: int = 1):
    """
    One point per independent group (no double counting of momentum):
    trend   close > EMA200 and EMA50 > EMA200
    momentum 126-day return > 0 and RSI(14) between 50 and 75
    volume  20-day up-volume share > 55% (accumulation)
    """

    def rule(df: pd.DataFrame) -> pd.DataFrame:
        close = df["close"]
        ema50 = EMAIndicator(close, window=50).ema_indicator()
        ema200 = EMAIndicator(close, window=200).ema_indicator()
        trend = (close > ema200) & (ema50 > ema200)
        rsi = RSIIndicator(close, window=14).rsi()
        momentum = (close / close.shift(126) - 1 > 0) & rsi.between(50, 75)
        vol = df["volume"].where(df["volume"] > 0).fillna(0)
        up = vol.where(close > close.shift(1), 0.0)
        volume = up.rolling(20).sum() / vol.rolling(20).sum() > 0.55
        score = trend.astype(int) + momentum.astype(int) + volume.astype(int)
        score = score.where(ema200.notna())
        return _frame(score >= enter_at, score <= exit_at, score.astype(float) + (close / ema200 - 1), df.index)

    rule.__name__ = f"grouped_{enter_at}_{exit_at}"
    return rule


CANDIDATES = {
    "breakout": (breakout_rule, [dict(entry_days=55, exit_days=20), dict(entry_days=20, exit_days=10), dict(entry_days=100, exit_days=40)]),
    "weekly_trend": (weekly_trend_rule, [dict(fast=10, slow=30), dict(fast=5, slow=20), dict(fast=13, slow=40)]),
    "dryup_breakout": (dryup_breakout_rule, [dict(dry_ratio=0.7), dict(dry_ratio=0.6), dict(dry_ratio=0.8)]),
    "grouped_score": (grouped_score_rule, [dict(enter_at=3, exit_at=1), dict(enter_at=3, exit_at=2), dict(enter_at=2, exit_at=0)]),
}

__all__ = ["breakout_rule", "weekly_trend_rule", "dryup_breakout_rule", "grouped_score_rule", "weekly_values", "CANDIDATES"]
