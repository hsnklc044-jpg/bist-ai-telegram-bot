"""
QuantBIST Framework
Market Models
"""

from __future__ import annotations

from dataclasses import dataclass


# =====================================================
# MARKET BREADTH
# =====================================================

@dataclass(slots=True)
class MarketBreadth:
    """
    Market breadth analysis.
    """

    status: str

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

    status: str

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

    status: str

    summary: str


# =====================================================
# MARKET STATUS
# =====================================================

@dataclass(slots=True)
class MarketStatus:
    """
    Complete market analysis.
    """

    status: str

    index: str

    change: float

    trend: str

    breadth: MarketBreadth

    sentiment: MarketSentiment

    volatility: str

    regime: MarketRegime

    @property
    def bullish(self) -> bool:

        return self.trend.upper() == "BULLISH"

    @property
    def bearish(self) -> bool:

        return self.trend.upper() == "BEARISH"

    @property
    def neutral(self) -> bool:

        return self.trend.upper() == "NEUTRAL"