"""
QuantBIST Framework
Decision Builder
"""

from __future__ import annotations

from core.committee.models import (
    CommitteeResult,
)

from core.decision.models import (
    Decision,
)

from core.market.models import (
    MarketStatus,
)

from core.portfolio.models import (
    PortfolioAnalysis,
)


# =====================================================
# HELPERS
# =====================================================

def _best_symbol(
    portfolio: PortfolioAnalysis,
) -> str:
    """
    Best portfolio position.
    """

    return portfolio.optimization.largest_position


def _worst_symbol(
    portfolio: PortfolioAnalysis,
) -> str:
    """
    Worst portfolio position.
    """

    return portfolio.optimization.smallest_position


def _warnings(
    portfolio: PortfolioAnalysis,
    market: MarketStatus,
) -> list[str]:
    """
    Generate warnings.
    """

    warnings: list[str] = []

    if portfolio.rebalance.needs_rebalance:

        warnings.append(
            "Portfolio rebalancing recommended."
        )

    if portfolio.optimization.concentration_risk:

        warnings.append(
            "Portfolio concentration risk detected."
        )

    if market.risk_off:

        warnings.append(
            "Market is currently Risk-Off."
        )

    if market.volatility.value == "HIGH":

        warnings.append(
            "High market volatility."
        )

    return warnings


def _suggestions(
    portfolio: PortfolioAnalysis,
    market: MarketStatus,
) -> list[str]:
    """
    Generate suggestions.
    """

    suggestions: list[str] = []

    if market.risk_on:

        suggestions.append(
            "Selective equity exposure can be increased."
        )

    if portfolio.rebalance.needs_rebalance:

        suggestions.append(
            "Review target portfolio weights."
        )

    if portfolio.health.score >= 80:

        suggestions.append(
            "Maintain current portfolio discipline."
        )

    if not suggestions:

        suggestions.append(
            "Monitor market developments."
        )

    return suggestions


# =====================================================
# PUBLIC API
# =====================================================

def build_decision(
    committee: CommitteeResult,
    portfolio: PortfolioAnalysis,
    market: MarketStatus,
) -> Decision:
    """
    Build final Decision model.
    """

    return Decision(

        action=committee.action.value,

        score=round(
            committee.score,
        ),

        confidence=committee.confidence,

        priority=committee.priority,

        summary=committee.summary,

        portfolio_health=portfolio.health.score,

        portfolio_grade=portfolio.health.grade,

        risk_level=portfolio.risk.level,

        market_status=market.status,

        market_trend=market.trend.value,

        market_regime=market.regime.status.value,

        best_symbol=_best_symbol(
            portfolio,
        ),

        worst_symbol=_worst_symbol(
            portfolio,
        ),

        rebalance_required=portfolio.rebalance.needs_rebalance,

        reasons=[
            vote.summary
            for vote in committee.votes
        ],

        suggestions=_suggestions(

            portfolio,

            market,

        ),

        warnings=_warnings(

            portfolio,

            market,

        ),

    )


# =====================================================
# EXPORTS
# =====================================================

__all__ = [

    "build_decision",

]