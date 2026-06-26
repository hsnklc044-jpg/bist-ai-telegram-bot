"""
QuantBIST RC4
Dashboard Service
"""

from __future__ import annotations


def get_dashboard_stats() -> dict:
    """
    Temporary dashboard data.

    This service will later be connected to the
    portfolio engine and market engine.
    """

    return {
        "portfolio": 0,
        "positions": 0,
        "cash": 0,
        "top_stock": "-",
        "sharpe": 0,
        "win_rate": 0,
        "profit_factor": 0,
        "max_drawdown": 0,
    }