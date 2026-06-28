"""
QuantBIST Framework
Portfolio Risk Engine
"""

from __future__ import annotations

from core.config.portfolio import (
    RISK_CRITICAL,
    RISK_HIGH,
    RISK_LOW,
    RISK_MEDIUM,
)

from core.infrastructure.exceptions import (
    PortfolioError,
)

from core.infrastructure.logger import (
    get_logger,
)

from core.portfolio.models import (
    PortfolioRisk,
    PortfolioStats,
)

logger = get_logger(__name__)


def calculate_portfolio_risk(
    stats: PortfolioStats,
) -> PortfolioRisk:
    """
    Calculate portfolio risk profile.

    Parameters
    ----------
    stats
        Portfolio statistics.

    Returns
    -------
    PortfolioRisk
    """

    logger.info(
        "Calculating portfolio risk..."
    )

    try:

        if stats.max_drawdown < 0:

            raise PortfolioError(
                "Maximum drawdown cannot be negative."
            )

        score = round(
            float(stats.max_drawdown),
            2,
        )

        # -------------------------------------------------
        # Risk Level
        # -------------------------------------------------

        if score < RISK_LOW:

            level = "LOW"

        elif score < RISK_MEDIUM:

            level = "MEDIUM"

        elif score < RISK_HIGH:

            level = "HIGH"

        elif score < RISK_CRITICAL:

            level = "VERY_HIGH"

        else:

            level = "CRITICAL"

        # -------------------------------------------------
        # Volatility Estimate
        # -------------------------------------------------

        volatility = round(
            score * 1.50,
            2,
        )

        # -------------------------------------------------
        # Summary
        # -------------------------------------------------

        summary = (
            f"{level} risk "
            f"(Drawdown {score:.2f}%)"
        )

        logger.info(
            "Portfolio risk calculated successfully."
        )

        return PortfolioRisk(

            level=level,

            score=score,

            volatility=volatility,

            max_drawdown=stats.max_drawdown,

            sharpe=stats.sharpe,

            summary=summary,

        )

    except PortfolioError:

        raise

    except Exception as exc:

        logger.exception(
            "Portfolio risk calculation failed."
        )

        raise PortfolioError(
            str(exc)
        ) from exc