"""
QuantBIST
Signal history.

Recomputes the live single-stock signal (core.analytics) for every
day of a price history. Each row only uses candles up to and including
that day, so a row's score is exactly what /analyze would have shown
after that session closed.
"""

from __future__ import annotations

import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator
from ta.volatility import AverageTrueRange

from core.analytics.scoring import calculate_score
from core.market.indicators import MIN_HISTORY_LENGTH

VOLUME_WINDOW = 20


def _volume_ratio(volume: pd.Series) -> pd.Series:
    """Same rule as the live analyzer: today / 20-day average, 1.0 when unknown."""

    average = volume.rolling(VOLUME_WINDOW).mean()
    ratio = (volume / average).round(2)

    return ratio.where(average > 0, 1.0).fillna(1.0)


def score_history(df: pd.DataFrame) -> pd.DataFrame:
    """
    Indicators, score and signal per day.

    Rows before MIN_HISTORY_LENGTH candles have no score (NaN), like
    the live analyzer, which refuses to score short histories.
    """

    close = df["close"]

    atr = AverageTrueRange(df["high"], df["low"], close, window=14).average_true_range()

    out = pd.DataFrame(
        {
            "close": close,
            "ema20": EMAIndicator(close, window=20).ema_indicator().round(4),
            "ema50": EMAIndicator(close, window=50).ema_indicator().round(4),
            "rsi": RSIIndicator(close, window=14).rsi().round(4),
            "macd": MACD(close).macd().round(4),
            "atr": atr.round(4),
            "volume_ratio": _volume_ratio(df["volume"]),
        },
        index=df.index,
    )
    out["volatility"] = (out["atr"] / close.round(4)).round(4)

    scores = []
    signals = []

    for position, row in enumerate(out.itertuples()):
        values = (row.ema20, row.ema50, row.rsi, row.macd, row.atr)

        if position < MIN_HISTORY_LENGTH - 1 or any(pd.isna(v) for v in values):
            scores.append(float("nan"))
            signals.append(None)
            continue

        result = calculate_score(
            ma20=row.ema20,
            ma50=row.ema50,
            rsi=row.rsi,
            macd=row.macd,
            volume_ratio=row.volume_ratio,
            volatility=row.volatility,
        )
        scores.append(result["score"])
        signals.append(result["signal"])

    out["score"] = scores
    out["signal"] = signals

    return out


__all__ = [
    "score_history",
]
