"""
QuantBIST RC4
Market Scanner
"""

from __future__ import annotations

from core.market.models import MarketStatus


def scan_market() -> MarketStatus:
    """
    Market Scanner.

    Şimdilik placeholder değerler döndürür.
    Daha sonra gerçek veri kaynaklarıyla beslenecektir.
    """

    return MarketStatus(

        status="OPEN",

        index="BIST100",

        change=1.24,

        trend="BULLISH",

        breadth="POSITIVE",

        sentiment="GREED",

        volatility="LOW",

        regime="RISK_ON",

    )