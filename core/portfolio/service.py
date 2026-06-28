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


def get_portfolio_analysis(
    stats: PortfolioStats,
) -> PortfolioAnalysis:
    """
    Public entry point for the Portfolio Engine.

    Parameters
    ----------
    stats
        Portfolio statistics.

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
            "Portfolio Service completed."
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