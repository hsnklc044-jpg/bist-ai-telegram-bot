"""
QuantBIST RC5
Portfolio Optimizer

Portfolio allocation intelligence engine.
"""

from __future__ import annotations


from core.config.portfolio import (
    MAX_POSITION_WEIGHT,
    TARGET_POSITION_WEIGHT,
)

from core.infrastructure.exceptions import (
    PortfolioOptimizationError,
)

from core.infrastructure.logger import (
    get_logger,
)

from core.portfolio.models import (
    PortfolioAction,
    PortfolioOptimization,
    PortfolioSeverity,
)

from core.portfolio.repository import (
    load_portfolio,
)


logger = get_logger(__name__)




# =====================================================
# HEALTH
# =====================================================


def _calculate_health_score(
    concentration_penalty: int,
    underweight_penalty: int,
) -> int:

    score = 100

    score -= concentration_penalty

    score -= underweight_penalty


    return max(
        0,
        min(
            score,
            100,
        ),
    )





# =====================================================
# SEVERITY
# =====================================================


def _determine_severity(
    score: int,
) -> PortfolioSeverity:


    if score >= 90:

        return PortfolioSeverity.LOW


    if score >= 75:

        return PortfolioSeverity.MEDIUM


    if score >= 60:

        return PortfolioSeverity.HIGH


    return PortfolioSeverity.CRITICAL





# =====================================================
# ACTION
# =====================================================


def _determine_action(
    severity: PortfolioSeverity,
) -> PortfolioAction:


    if severity is PortfolioSeverity.LOW:

        return PortfolioAction.HOLD


    if severity is PortfolioSeverity.MEDIUM:

        return PortfolioAction.REBALANCE


    if severity is PortfolioSeverity.HIGH:

        return PortfolioAction.REDUCE_RISK


    return PortfolioAction.REDUCE_RISK





# =====================================================
# PUBLIC API
# =====================================================


def optimize_portfolio(
    stats=None,
) -> PortfolioOptimization:
    """
    Analyze portfolio allocation.
    """


    logger.info(
        "Portfolio optimization started."
    )


    try:


        portfolio = load_portfolio()


        if portfolio.empty:


            return PortfolioOptimization(

                total_value=0.0,

                largest_position="-",

                largest_weight=0.0,

                smallest_position="-",

                smallest_weight=0.0,

                best_symbol="-",

                worst_symbol="-",

                concentration_risk=False,

                rebalance=False,

                health_score=100,

                severity=PortfolioSeverity.LOW,

                overall_action=PortfolioAction.HOLD,

            )





        total_value = float(
            portfolio["value"].sum()
        )


        if total_value <= 0:

            raise PortfolioOptimizationError(
                "Invalid portfolio value."
            )




        largest_position = "-"

        smallest_position = "-"


        largest_weight = 0.0

        smallest_weight = 100.0




        best_symbol = "-"

        worst_symbol = "-"




        concentration_risk = False

        rebalance = False



        concentration_penalty = 0

        underweight_penalty = 0



        suggestions = []





        for row in portfolio.itertuples(
            index=False
        ):


            symbol = str(
                row.symbol
            )


            value = float(
                row.value
            )


            weight = round(

                value
                /
                total_value
                *
                100,

                2,

            )




            if weight > largest_weight:

                largest_weight = weight

                largest_position = symbol




            if weight < smallest_weight:

                smallest_weight = weight

                smallest_position = symbol





            if weight > largest_weight:

                best_symbol = symbol





            if weight < smallest_weight:

                worst_symbol = symbol





            if weight > MAX_POSITION_WEIGHT:


                concentration_risk = True

                rebalance = True


                concentration_penalty += 10



                suggestions.append(

                    f"{symbol} ağırlığı yüksek "
                    f"({weight:.2f}%). Azaltılabilir."

                )





            elif weight < TARGET_POSITION_WEIGHT / 2:


                rebalance = True

                underweight_penalty += 5


                suggestions.append(

                    f"{symbol} düşük ağırlıkta "
                    f"({weight:.2f}%). Artırılabilir."

                )






        health_score = _calculate_health_score(

            concentration_penalty,

            underweight_penalty,

        )



        severity = _determine_severity(

            health_score,

        )



        action = _determine_action(

            severity,

        )





        return PortfolioOptimization(


            total_value=round(

                total_value,

                2,

            ),


            largest_position=largest_position,


            largest_weight=largest_weight,


            smallest_position=smallest_position,


            smallest_weight=smallest_weight,


            best_symbol=best_symbol,


            worst_symbol=worst_symbol,


            concentration_risk=concentration_risk,


            rebalance=rebalance,


            health_score=health_score,


            severity=severity,


            overall_action=action,


            suggestions=suggestions,

        )





    except PortfolioOptimizationError:

        raise



    except Exception as exc:


        logger.exception(
            "Portfolio optimization failed."
        )


        raise PortfolioOptimizationError(

            str(exc)

        ) from exc






__all__ = [

    "optimize_portfolio",

]