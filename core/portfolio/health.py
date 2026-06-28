"""
QuantBIST Framework
Portfolio Health Engine
"""

from __future__ import annotations

from core.config.portfolio import (
    HEALTH_EXCELLENT,
    HEALTH_GOOD,
    HEALTH_WARNING,
    IDEAL_CASH_RATIO,
)

from core.infrastructure.exceptions import (
    PortfolioError,
)

from core.infrastructure.logger import (
    get_logger,
)

from core.portfolio.models import (
    PortfolioHealth,
    PortfolioStats,
)

logger = get_logger(__name__)


def calculate_portfolio_health(
    stats: PortfolioStats,
) -> PortfolioHealth:
    """
    Calculate overall portfolio health.
    """

    logger.info(
        "Calculating portfolio health..."
    )

    try:

        if stats.portfolio < 0:

            raise PortfolioError(
                "Portfolio value cannot be negative."
            )

        # -------------------------------------------------
        # Cash Ratio
        # -------------------------------------------------

        cash_ratio = 0.0

        if stats.portfolio > 0:

            cash_ratio = round(
                stats.cash / stats.portfolio * 100,
                2,
            )

        # -------------------------------------------------
        # Diversification
        # -------------------------------------------------

        diversification = min(
            stats.positions * 10.0,
            100.0,
        )

        concentration = round(
            100.0 - diversification,
            2,
        )

        # -------------------------------------------------
        # Score
        # -------------------------------------------------

        score = 100.0

        if diversification < 50:
            score -= 20

        elif diversification < 70:
            score -= 10

        if cash_ratio < IDEAL_CASH_RATIO:
            score -= 10

        score = max(
            0.0,
            round(score, 2),
        )

        # -------------------------------------------------
        # Grade
        # -------------------------------------------------

        if score >= HEALTH_EXCELLENT:

            grade = "A"

        elif score >= HEALTH_GOOD:

            grade = "B"

        elif score >= HEALTH_WARNING:

            grade = "C"

        else:

            grade = "D"

        summary = (
            f"Portfolio Grade {grade} "
            f"({score:.0f}/100)"
        )

        logger.info(
            "Portfolio health calculated successfully."
        )

        return PortfolioHealth(

            score=score,

            grade=grade,

            diversification=diversification,

            concentration=concentration,

            cash_ratio=cash_ratio,

            summary=summary,

        )

    except PortfolioError:

        raise

    except Exception as exc:

        logger.exception(
            "Portfolio health calculation failed."
        )

        raise PortfolioError(
            str(exc)
        ) from exc