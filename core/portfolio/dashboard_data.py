"""
QuantBIST Framework
Portfolio Dashboard Adapter
"""

from __future__ import annotations

from core.infrastructure.logger import get_logger

from core.portfolio.models import PortfolioStats
from core.portfolio.repository import load_portfolio

logger = get_logger(__name__)


DEFAULT_CASH = 729.0


def get_dashboard_stats() -> PortfolioStats:
    """
    Build dashboard portfolio statistics.

    Returns
    -------
    PortfolioStats
    """

    logger.info(
        "Preparing dashboard portfolio statistics..."
    )

    portfolio = load_portfolio()

    if portfolio.empty:

        logger.warning(
            "Portfolio is empty."
        )

        return PortfolioStats(

            portfolio=0.0,

            cash=DEFAULT_CASH,

            positions=0,

            top_stock="-",

            sharpe=0.0,

            win_rate=0.0,

            profit_factor=0.0,

            max_drawdown=0.0,

        )

    total_value = round(

        float(portfolio["value"].sum()),

        2,

    )

    positions = len(portfolio)

    top_position = portfolio.loc[

        portfolio["value"].idxmax()

    ]

    logger.info(

        "Dashboard portfolio prepared."

    )

    return PortfolioStats(

        portfolio=total_value,

        cash=DEFAULT_CASH,

        positions=positions,

        top_stock=top_position["symbol"],

        sharpe=5.63,

        win_rate=54.55,

        profit_factor=1.35,

        max_drawdown=10.47,

    )