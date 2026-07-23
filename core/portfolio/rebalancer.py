"""
QuantBIST RC5
Portfolio Rebalancer Engine
"""

from __future__ import annotations


from core.infrastructure.exceptions import (
    PortfolioError,
)

from core.infrastructure.logger import (
    get_logger,
)

from core.portfolio.allocator import (
    allocate_portfolio,
)

from core.portfolio.models import (
    PortfolioOptimization,
    RebalanceResult,
)


logger = get_logger(__name__)





# =====================================================
# CONFIG
# =====================================================


DRIFT_THRESHOLD = 5.0






# =====================================================
# HELPERS
# =====================================================


def _action_value(
    action,
) -> str:

    if hasattr(
        action,
        "value",
    ):

        return action.value

    return str(action)






# =====================================================
# PUBLIC API
# =====================================================


def generate_rebalance_plan(
    optimization: PortfolioOptimization,
) -> RebalanceResult:
    """
    Generate RC5 rebalance plan.

    Uses:

    - Optimization result
    - Allocation drift
    - Target deviations

    """


    logger.info(
        "Generating rebalance plan."
    )


    try:


        if optimization is None:

            raise PortfolioError(
                "Optimization result missing."
            )



        allocations = allocate_portfolio()



        buy: list[str] = []

        sell: list[str] = []





        for item in allocations:


            drift = abs(
                float(
                    item.drift
                )
            )


            if drift < DRIFT_THRESHOLD:

                continue




            action = _action_value(
                item.action
            )



            if action == "INCREASE":

                buy.append(
                    item.symbol
                )



            elif action == "REDUCE":

                sell.append(
                    item.symbol
                )






        needs_rebalance = (

            optimization.rebalance

            or bool(buy)

            or bool(sell)

        )





        if needs_rebalance:


            summary = (

                f"Rebalance required "

                f"(Buy={len(buy)}, "

                f"Sell={len(sell)})"

            )



        else:


            summary = (

                "Portfolio allocation balanced."

            )






        result = RebalanceResult(

            needs_rebalance=needs_rebalance,

            summary=summary,

            buy=buy,

            sell=sell,

        )






        logger.info(

            "Rebalance completed | Required=%s",

            needs_rebalance,

        )



        return result





    except PortfolioError:

        raise





    except Exception as exc:


        logger.exception(

            "Rebalance generation failed."

        )


        raise PortfolioError(

            str(exc)

        ) from exc







# =====================================================
# METRICS
# =====================================================


def rebalance_score(
    optimization: PortfolioOptimization,
) -> float:
    """
    Calculate portfolio rebalance quality score.

    100 = Perfect balance

    """


    try:


        if optimization is None:

            return 0.0




        allocations = allocate_portfolio()



        if not allocations:

            return 100.0





        average_drift = (

            sum(

                abs(
                    float(item.drift)
                )

                for item in allocations

            )

            /

            len(allocations)

        )






        score = (

            100.0

            -

            average_drift * 5

        )





        if optimization.concentration_risk:

            score -= 15





        if optimization.rebalance:

            score -= 10





        return round(

            max(

                0.0,

                min(

                    score,

                    100.0,

                ),

            ),

            2,

        )





    except Exception as exc:


        logger.exception(

            "Rebalance score failed."

        )


        raise PortfolioError(

            str(exc)

        ) from exc






# =====================================================
# EXPORTS
# =====================================================


__all__ = [

    "generate_rebalance_plan",

    "rebalance_score",

]
