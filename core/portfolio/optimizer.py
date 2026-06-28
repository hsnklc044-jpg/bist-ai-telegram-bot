"""
QuantBIST Framework
Portfolio Optimizer
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
    PortfolioOptimization,
)

from core.portfolio.repository import (
    load_portfolio,
)

logger = get_logger(__name__)


def optimize_portfolio() -> PortfolioOptimization:
    """
    Analyze portfolio allocation and generate
    optimization recommendations.

    Returns
    -------
    PortfolioOptimization
    """

    logger.info(
        "Starting portfolio optimization..."
    )

    try:

        portfolio = load_portfolio()

        if portfolio.empty:

            logger.warning(
                "Portfolio is empty."
            )

            return PortfolioOptimization(

                total_value=0.0,

                largest_position="-",

                smallest_position="-",

                concentration_risk=False,

                rebalance=False,

                suggestions=[],

            )

        total_value = float(
            portfolio["value"].sum()
        )

        if total_value <= 0:

            raise PortfolioOptimizationError(
                "Total portfolio value must be positive."
            )

        largest_symbol = "-"
        smallest_symbol = "-"

        largest_weight = -1.0
        smallest_weight = 101.0

        concentration_risk = False
        rebalance = False

        suggestions: list[str] = []

        for _, row in portfolio.iterrows():

            symbol = str(row["symbol"])

            value = float(row["value"])

            weight = round(
                value / total_value * 100,
                2,
            )

            if weight > largest_weight:

                largest_weight = weight

                largest_symbol = symbol

            if weight < smallest_weight:

                smallest_weight = weight

                smallest_symbol = symbol

            if weight > MAX_POSITION_WEIGHT:

                concentration_risk = True
                rebalance = True

                suggestions.append(

                    f"Reduce {symbol} allocation "
                    f"({weight:.2f}%)"

                )

            elif weight < TARGET_POSITION_WEIGHT / 2:

                rebalance = True

                suggestions.append(

                    f"Increase {symbol} allocation "
                    f"({weight:.2f}%)"

                )

        logger.info(

            "Portfolio optimization completed "
            "(%d suggestion(s)).",

            len(suggestions),

        )

        return PortfolioOptimization(

            total_value=round(total_value, 2),

            largest_position=largest_symbol,

            smallest_position=smallest_symbol,

            concentration_risk=concentration_risk,

            rebalance=rebalance,

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