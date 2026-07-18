"""
QuantBIST Framework
Market Domain Models
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


# =====================================================
# ENUMS
# =====================================================

class MarketTrend(Enum):
    """
    Primary market trend.
    """

    BULLISH = "BULLISH"
    NEUTRAL = "NEUTRAL"
    BEARISH = "BEARISH"


class MarketRegimeType(Enum):
    """
    Portfolio allocation regime.
    """

    RISK_ON = "RISK_ON"
    NEUTRAL = "NEUTRAL"
    RISK_OFF = "RISK_OFF"


class BreadthStatus(Enum):
    """
    Market breadth condition.
    """

    POSITIVE = "POSITIVE"
    NEUTRAL = "NEUTRAL"
    NEGATIVE = "NEGATIVE"


class SentimentStatus(Enum):
    """
    Market sentiment.
    """

    GREED = "GREED"
    NEUTRAL = "NEUTRAL"
    FEAR = "FEAR"


class VolatilityLevel(Enum):
    """
    Market volatility level.
    """

    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"


# =====================================================
# RAW MARKET SNAPSHOT
# =====================================================

@dataclass(slots=True)
class MarketSnapshot:
    """
    Raw market data.

    Produced by Market Data Provider.
    """

    symbol: str

    last_price: float

    previous_close: float

    daily_change: float

    volume: float

    updated: datetime


# =====================================================
# TECHNICAL INDICATORS
# =====================================================

@dataclass(slots=True)
class IndicatorSnapshot:
    """
    Complete technical indicator snapshot.
    """

    symbol: str

    price: float

    volume: float

    ema20: float
    ema50: float
    ema200: float

    sma20: float
    sma50: float
    sma200: float

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


# =====================================================
# MARKET BREADTH
# =====================================================

@dataclass(slots=True)
class MarketBreadth:
    """
    Market breadth analysis.
    """

    status: BreadthStatus

    score: float

    summary: str


# =====================================================
# MARKET SENTIMENT
# =====================================================

@dataclass(slots=True)
class MarketSentiment:
    """
    Market sentiment analysis.
    """

    status: SentimentStatus

    score: float

    summary: str


# =====================================================
# MARKET REGIME
# =====================================================

@dataclass(slots=True)
class MarketRegime:
    """
    Current market regime.
    """

    status: MarketRegimeType

    score: float

    summary: str


# =====================================================
# MARKET STATUS
# =====================================================

@dataclass(slots=True)
class MarketStatus:
    """
    Complete market analysis.

    Shared across Dashboard,
    AI Engine,
    Decision Engine,
    Telegram,
    Morning Report.
    """

    status: str

    index: str

    change: float

    trend: MarketTrend

    volatility: VolatilityLevel

    breadth: MarketBreadth

    sentiment: MarketSentiment

    regime: MarketRegime

    indicators: IndicatorSnapshot | None = None

    updated: datetime | None = None

    @property
    def bullish(self) -> bool:

        return self.trend is MarketTrend.BULLISH

    @property
    def bearish(self) -> bool:

        return self.trend is MarketTrend.BEARISH

    @property
    def neutral(self) -> bool:

        return self.trend is MarketTrend.NEUTRAL

    @property
    def risk_on(self) -> bool:

        return self.regime.status is MarketRegimeType.RISK_ON

    @property
    def risk_off(self) -> bool:

        return self.regime.status is MarketRegimeType.RISK_OFF

    @property
    def market_score(self) -> float:
        """
        Composite market score.
        """

        return round(

            (
                self.breadth.score
                + self.sentiment.score
                + self.regime.score
            )
            / 3,

            2,

        )

    @property
    def healthy(self) -> bool:
        """
        True if market score is healthy.
        """

        return self.market_score >= 70

    @property
    def defensive(self) -> bool:
        """
        True if defensive positioning
        is recommended.
        """

        return self.regime.status is MarketRegimeType.RISK_OFF

    @property
    def aggressive(self) -> bool:
        """
        True if aggressive positioning
        is allowed.
        """

        return self.regime.status is MarketRegimeType.RISK_ON