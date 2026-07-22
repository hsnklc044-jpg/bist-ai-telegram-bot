"""
QuantBIST RC5
Portfolio Allocation Engine
"""

from __future__ import annotations


from dataclasses import dataclass


from core.config.portfolio import (
    MAX_POSITION_WEIGHT,
    TARGET_POSITION_WEIGHT,
)

from core.infrastructure.exceptions import (
    PortfolioError,
)

from core.infrastructure.logger import (
    get_logger,
)

from core.portfolio.repository import (
    load_portfolio,
)


logger = get_logger(__name__)





# =====================================================
# MODEL
# =====================================================


@dataclass(slots=True)
class Allocation:
    """
    Single portfolio allocation item.
    """

    symbol: str

    value: float

    current_weight: float

    target_weight: float

    drift: float

    action: str






# =====================================================
# HELPERS
# =====================================================


def _determine_action(
    weight: float,
) -> str:
    """
    Determine allocation action.
    """


    if weight > MAX_POSITION_WEIGHT:

        return "REDUCE"



    if weight < TARGET_POSITION_WEIGHT * 0.50:

        return "INCREASE"



    return "KEEP"






def _calculate_target(
    positions: int,
) -> float:
    """
    Calculate equal allocation target.
    """


    if positions <= 0:

        return 0.0



    return round(

        100 / positions,

        2,

    )






# =====================================================
# PUBLIC API
# =====================================================


def allocate_portfolio() -> list[Allocation]:
    """
    Calculate portfolio allocation.

    Flow:

        Portfolio
            ↓
        Weight Calculation
            ↓
        Drift Analysis
            ↓
        Action

    """


    logger.info(
        "Portfolio allocation started."
    )


    try:


        portfolio = load_portfolio()



        if portfolio is None or portfolio.empty:


            logger.warning(
                "Portfolio empty."
            )


            return []





        required_columns = {

            "symbol",

            "value",

        }



        if not required_columns.issubset(

            portfolio.columns

        ):

            raise PortfolioError(

                "Portfolio data missing required columns."

            )





        total_value = float(

            portfolio["value"].sum()

        )





        if total_value <= 0:

            raise PortfolioError(

                "Invalid portfolio value."

            )





        position_count = len(

            portfolio

        )





        target = _calculate_target(

            position_count,

        )





        allocations: list[Allocation] = []





        for row in portfolio.itertuples(

            index=False

        ):


            symbol = str(

                row.symbol

            )


            value = float(

                row.value

            )





            current_weight = round(

                value

                /

                total_value

                *

                100,

                2,

            )





            drift = round(

                current_weight - target,

                2,

            )





            allocations.append(

                Allocation(

                    symbol=symbol,

                    value=round(

                        value,

                        2,

                    ),

                    current_weight=current_weight,

                    target_weight=target,

                    drift=drift,

                    action=_determine_action(

                        current_weight,

                    ),

                )

            )







        allocations.sort(

            key=lambda item:

            (

                -item.current_weight,

                item.symbol,

            )

        )







        logger.info(

            "Allocation completed | Positions=%d",

            len(allocations),

        )



        return allocations






    except PortfolioError:

        raise





    except Exception as exc:


        logger.exception(

            "Portfolio allocation failed."

        )


        raise PortfolioError(

            str(exc)

        ) from exc







# =====================================================
# SUMMARY
# =====================================================


def allocation_summary() -> dict:
    """
    Generate allocation summary.
    """


    allocations = allocate_portfolio()





    if not allocations:


        return {


            "positions": 0,

            "largest": "-",

            "smallest": "-",

            "average_weight": 0.0,


        }






    largest = allocations[0]

    smallest = allocations[-1]





    average = round(

        sum(

            item.current_weight

            for item in allocations

        )

        /

        len(allocations),

        2,

    )






    return {


        "positions":

            len(allocations),



        "largest":

            largest.symbol,



        "smallest":

            smallest.symbol,



        "average_weight":

            average,


    }







# =====================================================
# EXPORTS
# =====================================================


__all__ = [

    "Allocation",

    "allocate_portfolio",

    "allocation_summary",

]