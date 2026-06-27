"""
QuantBIST RC4
Market Models
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class MarketStatus:
    """
    Market analysis result.
    """

    status: str
    index: str
    change: float
    trend: str
    breadth: str
    sentiment: str
    volatility: str
    regime: str

    @property
    def bullish(self) -> bool:
        return self.trend.upper() == "BULLISH"

    @property
    def bearish(self) -> bool:
        return self.trend.upper() == "BEARISH"

    @property
    def neutral(self) -> bool:
        return self.trend.upper() == "NEUTRAL"