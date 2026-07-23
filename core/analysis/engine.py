"""
QuantBIST RC4
Analysis Engine
"""

from __future__ import annotations

from core.market.analyzer import analyze_market
from core.portfolio.analyzer import analyze_portfolio


def analyze(
    stats,
) -> dict:
    """
    QuantBIST Analysis Engine.

    Framework içerisindeki tüm analiz motorlarını
    tek noktada birleştirir.

    Returns
    -------
    dict
        {
            "portfolio": ...,
            "market": ...,
        }
    """

    portfolio = analyze_portfolio(
        stats,
    )

    market = analyze_market()

    return {

        "portfolio": portfolio,

        "market": market,

    }
