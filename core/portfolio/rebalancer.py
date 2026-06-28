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

from core.portfolio.models import (
    RebalanceResult,
)

from core.portfolio.optimizer import (
    optimize_portfolio,
)

logger = get_logger(__name__)


def generate_rebalance_plan() -> RebalanceResult:
    """
    Generate a portfolio rebalance plan.

    Returns
    -------
    RebalanceResult
    """

    logger.info(
        "Generating portfolio rebalance plan..."
    )

    try:

        optimization = optimize_portfolio()

        if not optimization.rebalance:

            logger.info(
                "Portfolio is already balanced."
            )

            return RebalanceResult(

                needs_rebalance=False,

                summary="No rebalance required.",

                buy=[],

                sell=[],

            )

        buy: list[str] = []

        sell: list[str] = []

        for suggestion in optimization.suggestions:

            if suggestion.startswith("Increase"):

                buy.append(suggestion)

            elif suggestion.startswith("Reduce"):

                sell.append(suggestion)

        summary = (

            f"Buy: {len(buy)} | "
            f"Sell: {len(sell)}"

        )

        logger.info(
            "Rebalance plan created."
        )

        return RebalanceResult(

            needs_rebalance=True,

            summary=summary,

            buy=buy,

            sell=sell,

        )

    except PortfolioError:

        raise

    except Exception as exc:

        logger.exception(
            "Rebalance plan generation failed."
        )

        raise PortfolioError(
            str(exc)
        ) from exc