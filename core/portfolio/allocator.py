"""
QuantBIST Framework
Portfolio Allocator
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
# MODELS
# =====================================================

@dataclass(slots=True)
class Allocation:

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
    Calculate equal-weight target.
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

    Returns
    -------
    list[Allocation]
    """

    logger.info(
        "Calculating portfolio allocation..."
    )

    try:

        portfolio = load_portfolio()

        if portfolio.empty:

            logger.warning(
                "Portfolio is empty."
            )

            return []

        total_value = float(
            portfolio["value"].sum()
        )

        if total_value <= 0:

            raise PortfolioError(
                "Invalid portfolio value."
            )

        target = _calculate_target(
            len(portfolio)
        )

        allocations: list[Allocation] = []

        for _, row in portfolio.iterrows():

            symbol = str(
                row["symbol"]
            )

            value = float(
                row["value"]
            )

            current_weight = round(

                value / total_value * 100,

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

            key=lambda item: item.current_weight,

            reverse=True,

        )

        logger.info(

            "Portfolio allocation completed (%d positions).",

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
    Allocation summary.
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

        / len(allocations),

        2,

    )

    return {

        "positions": len(allocations),

        "largest": largest.symbol,

        "smallest": smallest.symbol,

        "average_weight": average,

    }


# =====================================================
# EXPORTS
# =====================================================

__all__ = [

    "Allocation",

    "allocate_portfolio",

    "allocation_summary",

]