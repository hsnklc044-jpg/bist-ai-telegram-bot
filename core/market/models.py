"""
QuantBIST RC5
Market Intelligence Domain Models
"""

from __future__ import annotations

from dataclasses import dataclass, field
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
    Market participation condition.
    """

    POSITIVE = "POSITIVE"

    NEUTRAL = "NEUTRAL"

    NEGATIVE = "NEGATIVE"




class SentimentStatus(Enum):
    """
    Investor sentiment state.
    """

    GREED = "GREED"

    NEUTRAL = "NEUTRAL"

    FEAR = "FEAR"




class VolatilityLevel(Enum):
    """
    Market volatility state.
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
    Raw market data snapshot.
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
    Technical indicator package.
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
    Market breadth intelligence.
    """


    status: BreadthStatus

    score: float

    summary: str


    factors: dict[str, float] = field(
        default_factory=dict,
    )





# =====================================================
# MARKET SENTIMENT
# =====================================================


@dataclass(slots=True)
class MarketSentiment:
    """
    Market psychology intelligence.
    """


    status: SentimentStatus

    score: float

    summary: str


    factors: dict[str, float] = field(
        default_factory=dict,
    )





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


    factors: dict[str, float] = field(
        default_factory=dict,
    )





# =====================================================
# MARKET STATUS
# =====================================================


@dataclass(slots=True)
class MarketStatus:
    """
    Complete market intelligence model.

    Used by:

    - Dashboard
    - AI Engine
    - Decision Engine
    - Reports

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


    updated: datetime = field(
        default_factory=datetime.now,
    )




    # =================================================
    # PROPERTIES
    # =================================================


    @property
    def bullish(
        self,
    ) -> bool:

        return self.trend is MarketTrend.BULLISH




    @property
    def bearish(
        self,
    ) -> bool:

        return self.trend is MarketTrend.BEARISH




    @property
    def neutral(
        self,
    ) -> bool:

        return self.trend is MarketTrend.NEUTRAL




    @property
    def risk_on(
        self,
    ) -> bool:

        return self.regime.status is MarketRegimeType.RISK_ON




    @property
    def risk_off(
        self,
    ) -> bool:

        return self.regime.status is MarketRegimeType.RISK_OFF




    @property
    def market_score(
        self,
    ) -> float:
        """
        Weighted market intelligence score.

        Regime      : 40%
        Breadth     : 35%
        Sentiment   : 25%

        """


        score = (

            self.regime.score * 0.40

            +

            self.breadth.score * 0.35

            +

            self.sentiment.score * 0.25

        )


        return round(
            score,
            2,
        )




    @property
    def healthy(
        self,
    ) -> bool:
        """
        Healthy market condition?
        """

        return self.market_score >= 70




    @property
    def defensive(
        self,
    ) -> bool:
        """
        Defensive positioning required?
        """

        return self.risk_off




    @property
    def aggressive(
        self,
    ) -> bool:
        """
        Aggressive positioning allowed?
        """

        return self.risk_on




    @property
    def summary(
        self,
    ) -> dict:
        """
        Dashboard friendly market summary.
        """

        return {

            "trend":
                self.trend.value,


            "regime":
                self.regime.status.value,


            "sentiment":
                self.sentiment.status.value,


            "breadth":
                self.breadth.status.value,


            "score":
                self.market_score,

        }





# =====================================================
# EXPORTS
# =====================================================

__all__ = [

    "MarketTrend",

    "MarketRegimeType",

    "BreadthStatus",

    "SentimentStatus",

    "VolatilityLevel",

    "MarketSnapshot",

    "IndicatorSnapshot",

    "MarketBreadth",

    "MarketSentiment",

    "MarketRegime",

    "MarketStatus",

]
