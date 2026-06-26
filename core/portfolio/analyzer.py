"""
QuantBIST RC4
Portfolio Analyzer
"""

from __future__ import annotations

from core.portfolio.health import calculate_portfolio_health


def analyze_portfolio(stats) -> dict:
    """
    Portföyü analiz eder.
    """

    health = calculate_portfolio_health(stats)

    if health["score"] >= 90:
        status = "Excellent"

    elif health["score"] >= 80:
        status = "Good"

    elif health["score"] >= 70:
        status = "Average"

    else:
        status = "Weak"

    return {

        "status": status,

        "health": health,

    }