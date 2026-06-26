"""
QuantBIST RC4
Portfolio Dashboard Data
"""

from __future__ import annotations

from core.portfolio.models import PortfolioStats
from core.portfolio.repository import load_portfolio


def get_dashboard_stats() -> PortfolioStats:
    """
    Generate dashboard statistics from portfolio data.
    """

    df = load_portfolio()

    if df.empty:
        return PortfolioStats(
            portfolio=0.0,
            cash=0.0,
            positions=0,
            top_stock="-",
            sharpe=0.0,
            win_rate=0.0,
            profit_factor=0.0,
            max_drawdown=0.0,
        )

    total_value = float(df["value"].sum())
    positions = len(df)

    top_stock = (
        df.sort_values(
            "value",
            ascending=False,
        )
        .iloc[0]["symbol"]
    )

    return PortfolioStats(
        portfolio=total_value,
        cash=729.0,
        positions=positions,
        top_stock=top_stock,
        sharpe=0.0,
        win_rate=0.0,
        profit_factor=0.0,
        max_drawdown=0.0,
    )