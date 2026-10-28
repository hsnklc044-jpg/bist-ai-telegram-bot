"""
QuantBIST
Technical score as a time series.

`score_frame(df)` computes, for every closed candle, exactly what the
live analyzer (core.analytics.analyzer.analyze_stock) would have shown
on that day: same indicators, same rounding, same thresholds. The
backtest uses it, so what is tested is what the bot sends.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator

from core.config.thresholds import (
    SIGNAL_BUY,
    SIGNAL_SELL,
    SIGNAL_STRONG_BUY,
    SIGNAL_STRONG_SELL,
)


def average_true_range(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
    """ta's AverageTrueRange, bit for bit (same true range, same seed, same recursion in the same
    order), on a numpy array instead of one pandas .iloc per row: ~50× faster on 5 years of data
    (test_screen_engine.FastAtrTest compares the two exactly)."""

    prev_close = close.shift(1)
    true_range = pd.DataFrame(
        data={"tr1": high - low, "tr2": (high - prev_close).abs(), "tr3": (low - prev_close).abs()}
    ).max(axis=1)
    atr = np.zeros(len(close))
    if len(atr) >= window:
        atr[window - 1] = true_range[0:window].mean()
        tr = true_range.to_numpy()
        for i in range(window, len(atr)):
            atr[i] = (atr[i - 1] * (window - 1) + tr[i]) / float(window)
    return pd.Series(data=atr, index=true_range.index, name="atr")


def volume_ratio_series(volume: pd.Series, window: int = 20) -> pd.Series:
    """Today's volume / mean of the previous `window` days (20 in the score); zero volume = missing."""

    v = volume.where(volume > 0)
    average = v.shift(1).rolling(window, min_periods=1).mean()
    ratio = (v / average).round(2)

    return ratio.where(average > 0).fillna(1.0)


def score_frame(df: pd.DataFrame) -> pd.DataFrame:
    """
    Columns: ema20, ema50, rsi, macd, volume_ratio, volatility,
    trend_pts, rsi_pts, macd_pts, volume_pts, volatility_pts,
    score, signal. Rows without enough history have NaN score.
    """

    close = df["close"]

    out = pd.DataFrame(index=df.index)
    out["ema20"] = EMAIndicator(close, window=20).ema_indicator().round(4)
    out["ema50"] = EMAIndicator(close, window=50).ema_indicator().round(4)
    out["rsi"] = RSIIndicator(close, window=14).rsi().round(4)
    out["macd"] = MACD(close).macd().round(4)
    atr = average_true_range(df["high"], df["low"], close, window=14)
    out["volatility"] = (atr.round(4) / close.round(4)).round(4)
    out["volume_ratio"] = volume_ratio_series(df["volume"])

    out["trend_pts"] = np.where(out["ema20"] > out["ema50"], 25, -25)
    out["rsi_pts"] = np.select(
        [out["rsi"] < 30, out["rsi"] < 40, out["rsi"] > 80, out["rsi"] > 70],
        [20, 10, -15, -10],
        0,
    )
    out["macd_pts"] = np.where(out["macd"] > 0, 15, -15)
    out["volume_pts"] = np.select(
        [out["volume_ratio"] > 1.10, out["volume_ratio"] < 0.80], [10, -10], 0
    )
    out["volatility_pts"] = np.select(
        [out["volatility"] < 0.03, out["volatility"] > 0.06], [10, -10], 0
    )

    raw = out[["trend_pts", "rsi_pts", "macd_pts", "volume_pts", "volatility_pts"]].sum(axis=1)
    score = (50 + raw).clip(0, 100)

    ready = out[["ema20", "ema50", "rsi", "macd", "volatility"]].notna().all(axis=1)
    out["score"] = score.where(ready)

    out["signal"] = np.select(
        [
            out["score"] >= SIGNAL_STRONG_BUY,
            out["score"] >= SIGNAL_BUY,
            out["score"] <= SIGNAL_STRONG_SELL,
            out["score"] <= SIGNAL_SELL,
        ],
        ["STRONG BUY", "BUY", "STRONG SELL", "SELL"],
        "WATCH",
    )
    out.loc[~ready, "signal"] = None

    return out


__all__ = [
    "average_true_range",
    "volume_ratio_series",
    "score_frame",
]
