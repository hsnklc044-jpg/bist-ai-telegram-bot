"""
QuantBIST RC4
Market Analyzer
"""

from __future__ import annotations

from core.market.scanner import scan_market


def analyze_market():
    """
    Market analizinin tek giriş noktası.
    """

    market = scan_market()

    return {

        "status": market.status,

        "index": market.index,

        "change": market.change,

        "trend": market.trend,

        "breadth": market.breadth,

        "sentiment": market.sentiment,

        "volatility": market.volatility,

        "regime": market.regime,

        "bullish": market.bullish,

        "bearish": market.bearish,

        "neutral": market.neutral,

    }