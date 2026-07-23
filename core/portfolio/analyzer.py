"""
QuantBIST RC5
Portfolio Analyzer

Main portfolio intelligence orchestrator.
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


def analyze_portfolio(
    stats: PortfolioStats,
) -> PortfolioAnalysis:
    """
    Execute complete RC5 Portfolio Intelligence Engine.

    Flow:

        Portfolio Stats
              |
              ↓
        Health Engine
              |
              ↓
        Risk Engine
              |
              ↓
        Optimization
              |
              ↓
        Rebalance
              |
              ↓
        Portfolio Analysis

    """


    logger.info(
        "Portfolio analysis started."
    )


    try:


        if stats is None:

            raise PortfolioError(
                "Portfolio stats cannot be empty."
            )



        # -----------------------------------------
        # Health Analysis
        # -----------------------------------------


        logger.debug(
            "Calculating portfolio health."
        )


        health = calculate_portfolio_health(
            stats,
        )


        if health is None:

            raise PortfolioError(
                "Health engine returned empty result."
            )




        # -----------------------------------------
        # Risk Analysis
        # -----------------------------------------


        logger.debug(
            "Calculating portfolio risk."
        )


        risk = calculate_portfolio_risk(
            stats,
        )


        if risk is None:

            raise PortfolioError(
                "Risk engine returned empty result."
            )





        # -----------------------------------------
        # Portfolio Optimization
        # -----------------------------------------


        logger.debug(
            "Running portfolio optimization."
        )


        optimization = optimize_portfolio(
            stats,
        )


        if optimization is None:

            raise PortfolioError(
                "Optimizer returned empty result."
            )






        # -----------------------------------------
        # Rebalance Planning
        # -----------------------------------------


        logger.debug(
            "Generating rebalance plan."
        )


        rebalance = generate_rebalance_plan(
            optimization,
        )


        if rebalance is None:

            raise PortfolioError(
                "Rebalance engine returned empty result."
            )






        # -----------------------------------------
        # Final Model
        # -----------------------------------------


        analysis = PortfolioAnalysis(

            stats=stats,

            health=health,

            risk=risk,

            optimization=optimization,

            rebalance=rebalance,

        )





        logger.info(

            "Portfolio completed | Health=%s | Risk=%s",

            health.grade,

            _enum_value(
                risk.level
            ),

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






# =====================================================
# EXPORTS
# =====================================================


__all__ = [

    "analyze_portfolio",

]
