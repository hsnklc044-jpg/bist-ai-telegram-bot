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
    PortfolioAction,
    PortfolioOptimization,
    PortfolioSeverity,
)

from core.portfolio.repository import (
    load_portfolio,
)

logger = get_logger(__name__)


def _calculate_health_score(
    concentration_penalty: int,
    underweight_penalty: int,
) -> int:
    """
    Calculate portfolio health score.
    """

    score = 100

    score -= concentration_penalty
    score -= underweight_penalty

    return max(score, 0)


def _determine_severity(
    score: int,
) -> PortfolioSeverity:
    """
    Determine optimization severity.
    """

    if score >= 90:
        return PortfolioSeverity.LOW

    if score >= 75:
        return PortfolioSeverity.MEDIUM

    if score >= 60:
        return PortfolioSeverity.HIGH

    return PortfolioSeverity.CRITICAL


def _determine_action(
    severity: PortfolioSeverity,
) -> PortfolioAction:
    """
    Determine final optimizer action.
    """

    match severity:

        case PortfolioSeverity.LOW:
            return PortfolioAction.HOLD

        case PortfolioSeverity.MEDIUM:
            return PortfolioAction.BUY

        case PortfolioSeverity.HIGH:
            return PortfolioAction.REBALANCE

        case _:
            return PortfolioAction.REDUCE_RISK


def optimize_portfolio() -> PortfolioOptimization:
    """
    Analyze portfolio allocation and
    generate optimization recommendations.
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
                largest_weight=0.0,

                smallest_position="-",
                smallest_weight=0.0,

                concentration_risk=False,

                rebalance=False,

                health_score=100,

                severity=PortfolioSeverity.LOW,

                overall_action=PortfolioAction.HOLD,

                suggestions=[],

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

        largest_weight = float("-inf")
        smallest_weight = float("inf")

        concentration_risk = False
        rebalance = False

        concentration_penalty = 0
        underweight_penalty = 0

        suggestions: list[str] = []

        for row in portfolio.itertuples(index=False):

            symbol = str(row.symbol)

            value = float(row.value)

            weight = round(
                value / total_value * 100,
                2,
            )

            if weight > largest_weight:

                largest_weight = weight
                largest_position = symbol

            if weight < smallest_weight:

                smallest_weight = weight
                smallest_position = symbol

            if weight > MAX_POSITION_WEIGHT:

                concentration_risk = True
                rebalance = True

                concentration_penalty += 15

                difference = round(
                    weight - TARGET_POSITION_WEIGHT,
                    2,
                )

                suggestions.append(

                    (
                        f"Reduce {symbol}: "
                        f"{weight:.2f}% → "
                        f"{TARGET_POSITION_WEIGHT:.2f}% "
                        f"(-{difference:.2f}%)"
                    )

                )

            elif weight < TARGET_POSITION_WEIGHT / 2:

                rebalance = True

                underweight_penalty += 5

                difference = round(
                    TARGET_POSITION_WEIGHT - weight,
                    2,
                )

                suggestions.append(

                    (
                        f"Increase {symbol}: "
                        f"{weight:.2f}% → "
                        f"{TARGET_POSITION_WEIGHT:.2f}% "
                        f"(+{difference:.2f}%)"
                    )

                )

        health_score = _calculate_health_score(

            concentration_penalty,

            underweight_penalty,

        )

        severity = _determine_severity(
            health_score
        )

        action = _determine_action(
            severity
        )

        logger.info(

            "Portfolio optimization completed | "
            "Health=%d | Severity=%s | Action=%s | Suggestions=%d",

            health_score,

            severity.value,

            action.value,

            len(suggestions),

        )

        return PortfolioOptimization(

            total_value=round(total_value, 2),

            largest_position=largest_position,

            largest_weight=round(
                largest_weight,
                2,
            ),

            smallest_position=smallest_position,

            smallest_weight=round(
                smallest_weight,
                2,
            ),

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