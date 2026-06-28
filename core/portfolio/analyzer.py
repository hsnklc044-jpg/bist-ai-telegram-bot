"""
QuantBIST Framework
Portfolio Analyzer
"""

from __future__ import annotations

from core.infrastructure.exceptions import (
    PortfolioError,
)

from core.infrastructure.logger import (
    get_logger,
)

from core.portfolio.health import (
    calculate_portfolio_health,
)

from core.portfolio.models import (
    PortfolioAnalysis,
    PortfolioStats,
)

from core.portfolio.optimizer import (
    optimize_portfolio,
)

from core.portfolio.rebalancer import (
    generate_rebalance_plan,
)

from core.portfolio.risk import (
    calculate_portfolio_risk,
)

logger = get_logger(__name__)


def analyze_portfolio(
    stats: PortfolioStats,
) -> PortfolioAnalysis:
    """
    Execute the complete Portfolio Engine.

    Parameters
    ----------
    stats
        Portfolio dashboard statistics.

    Returns
    -------
    PortfolioAnalysis
    """

    logger.info(
        "Portfolio analysis started."
    )

    try:

        # -----------------------------------------
        # Health
        # -----------------------------------------

        health = calculate_portfolio_health(
            stats,
        )

        # -----------------------------------------
        # Risk
        # -----------------------------------------

        risk = calculate_portfolio_risk(
            stats,
        )

        # -----------------------------------------
        # Optimization
        # -----------------------------------------

        optimization = optimize_portfolio()

        # -----------------------------------------
        # Rebalance
        # -----------------------------------------

        rebalance = generate_rebalance_plan(
            optimization,
        )

        analysis = PortfolioAnalysis(

            stats=stats,

            health=health,

            risk=risk,

            optimization=optimization,

            rebalance=rebalance,

        )

        logger.info(
            "Portfolio analysis completed."
        )

        return analysis

    except PortfolioError:

        raise

    except Exception as exc:

        logger.exception(
            "Portfolio analysis failed."
        )

        raise PortfolioError(
            str(exc)
        ) from exc