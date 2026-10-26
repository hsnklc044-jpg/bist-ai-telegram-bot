"""
QuantBIST
Market domain models.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MarketTrend(Enum):
    """Primary trend from the EMA20 / EMA50 / EMA200 stack."""

    BULLISH = "BULLISH"
    NEUTRAL = "NEUTRAL"
    BEARISH = "BEARISH"


@dataclass(slots=True)
class IndicatorSnapshot:
    """Technical indicators on the latest closed candle."""

    symbol: str
    price: float
    volume: float

    ema20: float
    ema50: float
    ema200: float | None

    sma20: float
    sma50: float
    sma200: float | None

    rsi: float
    atr: float

    macd: float
    macd_signal: float
    macd_histogram: float

    bollinger_upper: float
    bollinger_middle: float
    bollinger_lower: float

    trend: MarketTrend
    momentum: str


__all__ = [
    "MarketTrend",
    "IndicatorSnapshot",
]
