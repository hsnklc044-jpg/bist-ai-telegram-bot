"""
QuantBIST Framework
Decision Reason Engine
"""

from __future__ import annotations

from core.market.models import MarketStatus
from core.portfolio.models import PortfolioAnalysis


# =====================================================
# HELPERS
# =====================================================

def _portfolio_reasons(
    portfolio: PortfolioAnalysis,
) -> list[str]:
    """
    Portfolio related reasons.
    """

    reasons: list[str] = []

    health = portfolio.health.score

    if health >= 90:

        reasons.append(
            "Portfolio health is excellent."
        )

    elif health >= 75:

        reasons.append(
            "Portfolio health is strong."
        )

    elif health >= 60:

        reasons.append(
            "Portfolio health is acceptable."
        )

    else:

        reasons.append(
            "Portfolio health requires improvement."
        )

    reasons.append(
        f"Portfolio grade: {portfolio.health.grade}"
    )

    return reasons


# =====================================================
# RISK
# =====================================================

def _risk_reasons(
    portfolio: PortfolioAnalysis,
) -> list[str]:
    """
    Portfolio risk reasons.
    """

    reasons: list[str] = []

    level = portfolio.risk.level.upper()

    if level == "LOW":

        reasons.append(
            "Portfolio risk is low."
        )

    elif level == "MEDIUM":

        reasons.append(
            "Portfolio risk is under control."
        )

    elif level == "HIGH":

        reasons.append(
            "Portfolio risk is elevated."
        )

    else:

        reasons.append(
            "Portfolio risk is critical."
        )

    return reasons


# =====================================================
# MARKET
# =====================================================

def _market_reasons(
    market: MarketStatus,
) -> list[str]:
    """
    Market related reasons.
    """

    reasons: list[str] = []

    regime = market.regime.status.upper()

    if regime == "RISK_ON":

        reasons.append(
            "Market regime supports taking risk."
        )

    elif regime == "NEUTRAL":

        reasons.append(
            "Market regime is neutral."
        )

    else:

        reasons.append(
            "Market regime favors defensive positioning."
        )

    breadth = market.breadth.status.upper()

    if breadth == "POSITIVE":

        reasons.append(
            "Market breadth is positive."
        )

    elif breadth == "NEGATIVE":

        reasons.append(
            "Market breadth is weak."
        )

    sentiment = market.sentiment.status.upper()

    if sentiment == "GREED":

        reasons.append(
            "Investor sentiment is optimistic."
        )

    elif sentiment == "FEAR":

        reasons.append(
            "Investor sentiment is defensive."
        )

    return reasons


# =====================================================
# OPTIMIZATION
# =====================================================

def _optimization_reasons(
    portfolio: PortfolioAnalysis,
) -> list[str]:
    """
    Portfolio optimization reasons.
    """

    reasons: list[str] = []

    optimization = portfolio.optimization

    if optimization.rebalance:

        reasons.append(
            "Portfolio rebalancing is recommended."
        )

    else:

        reasons.append(
            "Portfolio allocation is balanced."
        )

    if optimization.concentration_risk:

        reasons.append(
            "Portfolio concentration risk detected."
        )

    else:

        reasons.append(
            "Portfolio concentration is within limits."
        )

    if optimization.suggestions:

        reasons.append(
            f"{len(optimization.suggestions)} optimization suggestion(s) available."
        )

    return reasons


# =====================================================
# AI
# =====================================================

def _ai_reasons(
    ai_score: int,
) -> list[str]:
    """
    AI score interpretation.
    """

    reasons: list[str] = []

    if ai_score >= 90:

        reasons.append(
            "AI conviction is extremely strong."
        )

    elif ai_score >= 75:

        reasons.append(
            "AI conviction is strong."
        )

    elif ai_score >= 60:

        reasons.append(
            "AI conviction is moderate."
        )

    elif ai_score >= 40:

        reasons.append(
            "AI conviction is weak."
        )

    else:

        reasons.append(
            "AI conviction is very weak."
        )

    return reasons


# =====================================================
# PUBLIC API
# =====================================================

def build_reasons(
    ai_score: int,
    portfolio: PortfolioAnalysis,
    market: MarketStatus,
) -> list[str]:
    """
    Build complete explanation list
    for the investment decision.
    """

    reasons: list[str] = []

    reasons.extend(
        _portfolio_reasons(
            portfolio,
        )
    )

    reasons.extend(
        _risk_reasons(
            portfolio,
        )
    )

    reasons.extend(
        _market_reasons(
            market,
        )
    )

    reasons.extend(
        _optimization_reasons(
            portfolio,
        )
    )

    reasons.extend(
        _ai_reasons(
            ai_score,
        )
    )

    # Remove duplicates while preserving order

    unique: list[str] = []

    for reason in reasons:

        if reason not in unique:

            unique.append(reason)

    return unique
