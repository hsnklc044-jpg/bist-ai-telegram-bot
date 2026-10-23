"""
QuantBIST RC5
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





# =====================================================
# HELPERS
# =====================================================


def _cash_ratio(
    stats: PortfolioStats,
) -> float:
    """
    Calculate portfolio cash ratio.
    """


    total_value = (

        stats.portfolio

        +

        stats.cash

    )


    if total_value <= 0:

        return 0.0



    return round(

        stats.cash

        /

        total_value

        *

        100,

        2,

    )







def _diversification_score(
    positions: int,
) -> float:
    """
    Calculate diversification score.
    """


    if positions <= 0:

        return 0.0



    return min(

        positions * 10.0,

        100.0,

    )







def _health_score(
    diversification: float,
    cash_ratio: float,
) -> float:
    """
    Calculate final portfolio health.
    """


    score = 100.0



    if diversification < 50:

        score -= 20



    elif diversification < 70:

        score -= 10





    if cash_ratio < IDEAL_CASH_RATIO:

        score -= 10





    return round(

        max(

            0.0,

            score,

        ),

        2,

    )







def _grade(
    score: float,
) -> str:
    """
    Convert health score into grade.
    """


    if score >= HEALTH_EXCELLENT:

        return "A"



    if score >= HEALTH_GOOD:

        return "B"



    if score >= HEALTH_WARNING:

        return "C"



    return "D"







# =====================================================
# PUBLIC API
# =====================================================


def calculate_portfolio_health(
    stats: PortfolioStats,
) -> PortfolioHealth:
    """
    Calculate RC5 portfolio health intelligence.
    """


    logger.info(

        "Portfolio health calculation started."

    )


    try:



        if stats.portfolio < 0:

            raise PortfolioError(

                "Portfolio value cannot be negative."

            )





        cash_ratio = _cash_ratio(

            stats,

        )





        diversification = _diversification_score(

            stats.positions,

        )





        concentration = round(

            100.0 - diversification,

            2,

        )





        score = _health_score(

            diversification,

            cash_ratio,

        )





        grade = _grade(

            score,

        )





        summary = (

            f"Portfolio Grade {grade} "

            f"({score:.0f}/100)"

        )





        logger.info(

            "Portfolio health completed | Grade=%s Score=%.2f",

            grade,

            score,

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

            "Portfolio health failed."

        )


        raise PortfolioError(

            str(exc)

        ) from exc







# =====================================================
# EXPORTS
# =====================================================


__all__ = [

    "calculate_portfolio_health",

]
