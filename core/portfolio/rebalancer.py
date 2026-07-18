"""
QuantBIST Framework
Portfolio Rebalancer
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
# PUBLIC API
# =====================================================

def generate_rebalance_plan(
    optimization: PortfolioOptimization,
) -> RebalanceResult:
    """
    Generate portfolio rebalance plan.
    """

    logger.info(
        "Generating rebalance plan..."
    )

    try:

        allocations = allocate_portfolio()

        buy: list[str] = []

        sell: list[str] = []

        for item in allocations:

            if item.action == "INCREASE":

                buy.append(item.symbol)

            elif item.action == "REDUCE":

                sell.append(item.symbol)

        needs_rebalance = (

            optimization.rebalance

            or len(buy) > 0

            or len(sell) > 0

        )

        if not needs_rebalance:

            summary = (
                "Portfolio allocation is balanced."
            )

        else:

            summary = (
                f"Rebalance required "
                f"(Buy: {len(buy)}, "
                f"Sell: {len(sell)})."
            )

        result = RebalanceResult(

            needs_rebalance=needs_rebalance,

            summary=summary,

            buy=buy,

            sell=sell,

        )

        logger.info(
            "Rebalance plan generated."
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
    Portfolio rebalance quality score.
    """

    allocations = allocate_portfolio()

    if not allocations:

        return 100.0

    drift = sum(

        abs(item.drift)

        for item in allocations

    ) / len(allocations)

    score = max(

        0.0,

        100.0 - drift * 5,

    )

    if optimization.concentration_risk:

        score -= 15

    if optimization.rebalance:

        score -= 10

    return round(

        max(score, 0.0),

        2,

    )


# =====================================================
# EXPORTS
# =====================================================

__all__ = [

    "generate_rebalance_plan",

    "rebalance_score",

]