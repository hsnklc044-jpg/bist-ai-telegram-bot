"""
QuantBIST RC4
Portfolio Analyzer
"""

from __future__ import annotations

from core.portfolio.health import calculate_portfolio_health
from core.portfolio.optimizer import optimize_portfolio
from core.portfolio.allocator import calculate_target_allocations
from core.portfolio.rebalancer import generate_rebalance_plan
from core.portfolio.risk import calculate_risk


def analyze_portfolio(stats) -> dict:
    """
    RC4 Portfolio Analysis Engine.

    Bu modül Dashboard, Telegram ve AI için
    portföy analizinin merkezidir.
    """

    health = calculate_portfolio_health(stats)

    risk = calculate_risk(stats)

    optimization = optimize_portfolio()

    allocation = calculate_target_allocations()

    rebalance = generate_rebalance_plan()

    return {

        "health": health,

        "risk": risk,

        "optimization": optimization,

        "allocation": allocation,

        "rebalance": rebalance,

    }