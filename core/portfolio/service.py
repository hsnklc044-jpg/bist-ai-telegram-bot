"""
QuantBIST RC5
Portfolio Intelligence Service
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
# HELPERS
# =====================================================


def _enum_value(
    value,
) -> str:

    if hasattr(
        value,
        "value",
    ):

        return value.value

    return str(value)





# =====================================================
# PUBLIC API
# =====================================================


def get_portfolio_analysis(
    stats: PortfolioStats,
) -> PortfolioAnalysis:
    """
    Execute complete portfolio intelligence engine.

    Flow:

        Portfolio Stats
              ↓
        Portfolio Analyzer
              ↓
        Portfolio Analysis

    """


    logger.info(
        "Portfolio Intelligence started."
    )


    try:


        if stats is None:

            raise PortfolioError(
                "Portfolio stats cannot be empty."
            )



        analysis = analyze_portfolio(
            stats,
        )



        if analysis is None:

            raise PortfolioError(
                "Portfolio analyzer returned empty result."
            )



        logger.info(

            "Portfolio completed | Health=%s | Risk=%s",

            analysis.health.grade,

            _enum_value(
                analysis.risk.level
            ),

        )



        return analysis



    except PortfolioError:

        raise



    except Exception as exc:


        logger.exception(

            "Portfolio Intelligence failed."

        )


        raise PortfolioError(

            str(exc)

        ) from exc






# =====================================================
# HEALTH
# =====================================================


def is_healthy(
    analysis: PortfolioAnalysis,
) -> bool:
    """
    Portfolio health check.
    """


    return analysis.health.score >= 80






def health_score(
    analysis: PortfolioAnalysis,
) -> float:
    """
    Return portfolio health score.
    """


    return float(
        analysis.health.score
    )





def portfolio_grade(
    analysis: PortfolioAnalysis,
) -> str:
    """
    Return portfolio grade.
    """


    return analysis.health.grade





# =====================================================
# RISK
# =====================================================


def risk_level(
    analysis: PortfolioAnalysis,
) -> str:
    """
    Return portfolio risk level.
    """


    return _enum_value(
        analysis.risk.level
    )





def risk_score(
    analysis: PortfolioAnalysis,
) -> float:
    """
    Return portfolio risk score.
    """


    return float(
        analysis.risk.score
    )





def has_concentration_risk(
    analysis: PortfolioAnalysis,
) -> bool:
    """
    Concentration risk check.
    """


    return bool(

        analysis.optimization.concentration_risk

    )






# =====================================================
# REBALANCE
# =====================================================


def needs_rebalance(
    analysis: PortfolioAnalysis,
) -> bool:
    """
    Portfolio rebalance requirement.
    """


    return bool(

        analysis.rebalance.needs_rebalance

    )






# =====================================================
# VALUE
# =====================================================


def portfolio_value(
    analysis: PortfolioAnalysis,
) -> float:
    """
    Total portfolio value.
    """


    return float(

        analysis.optimization.total_value

    )






def top_position(
    analysis: PortfolioAnalysis,
) -> str:
    """
    Largest portfolio position.
    """


    return analysis.optimization.largest_position






def bottom_position(
    analysis: PortfolioAnalysis,
) -> str:
    """
    Smallest portfolio position.
    """


    return analysis.optimization.smallest_position







# =====================================================
# SUMMARY
# =====================================================


def portfolio_summary(
    analysis: PortfolioAnalysis,
) -> dict[str, object]:
    """
    RC5 portfolio intelligence summary.
    """


    return {


        "health":

            float(
                analysis.health.score
            ),



        "grade":

            analysis.health.grade,



        "risk":

            _enum_value(
                analysis.risk.level
            ),



        "risk_score":

            float(
                analysis.risk.score
            ),



        "rebalance":

            bool(
                analysis.rebalance.needs_rebalance
            ),



        "largest_position":

            analysis.optimization.largest_position,



        "smallest_position":

            analysis.optimization.smallest_position,



        "concentration_risk":

            bool(
                analysis.optimization.concentration_risk
            ),

    }






# =====================================================
# EXPORTS
# =====================================================


__all__ = [

    "get_portfolio_analysis",

    "is_healthy",

    "health_score",

    "portfolio_grade",

    "needs_rebalance",

    "has_concentration_risk",

    "portfolio_value",

    "top_position",

    "bottom_position",

    "risk_level",

    "risk_score",

    "portfolio_summary",

]