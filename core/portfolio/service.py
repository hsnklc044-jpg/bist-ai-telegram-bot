"""
QuantBIST Framework
Portfolio Service
"""

from __future__ import annotations

from core.infrastructure.exceptions import (
    PortfolioError,
)

from core.infrastructure.logger import (
    get_logger,
)

from core.portfolio.analyzer import (
    analyze_portfolio,
)

from core.portfolio.models import (
    PortfolioAnalysis,
    PortfolioStats,
)

logger = get_logger(__name__)


# =====================================================
# PUBLIC API
# =====================================================

def get_portfolio_analysis(
    stats: PortfolioStats,
) -> PortfolioAnalysis:
    """
    Execute the complete Portfolio Engine.

    This service is the single public entry point for
    portfolio analysis.

    Parameters
    ----------
    stats
        Portfolio dashboard statistics.

    Returns
    -------
    PortfolioAnalysis
    """

    logger.info(
        "Portfolio Service started."
    )

    try:

        analysis = analyze_portfolio(
            stats,
        )

        logger.info(

            "Portfolio Service completed "
            "(Health=%s Risk=%s)",

            analysis.health.grade,

            analysis.risk.level,

        )

        return analysis

    except PortfolioError:

        raise

    except Exception as exc:

        logger.exception(
            "Portfolio Service failed."
        )

        raise PortfolioError(
            str(exc)
        ) from exc


# =====================================================
# HELPERS
# =====================================================

def is_healthy(
    analysis: PortfolioAnalysis,
) -> bool:
    """
    Returns True if portfolio health
    is considered healthy.
    """

    return analysis.health.score >= 80


def needs_rebalance(
    analysis: PortfolioAnalysis,
) -> bool:
    """
    Returns True if portfolio
    requires rebalancing.
    """

    return analysis.rebalance.needs_rebalance


def has_concentration_risk(
    analysis: PortfolioAnalysis,
) -> bool:
    """
    Returns True if concentration
    risk exists.
    """

    return analysis.optimization.concentration_risk


def portfolio_value(
    analysis: PortfolioAnalysis,
) -> float:
    """
    Returns current portfolio value.
    """

    return analysis.optimization.total_value


def top_position(
    analysis: PortfolioAnalysis,
) -> str:
    """
    Returns the largest portfolio position.
    """

    return analysis.optimization.largest_position


def risk_level(
    analysis: PortfolioAnalysis,
) -> str:
    """
    Returns portfolio risk level.
    """

    return analysis.risk.level


# =====================================================
# EXPORTS
# =====================================================

__all__ = [

    "get_portfolio_analysis",

    "is_healthy",

    "needs_rebalance",

    "has_concentration_risk",

    "portfolio_value",

    "top_position",

    "risk_level",

]