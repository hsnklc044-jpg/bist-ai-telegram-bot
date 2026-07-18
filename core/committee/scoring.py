"""
QuantBIST Framework
Investment Committee Scoring
"""

from __future__ import annotations

from core.infrastructure.logger import (
    get_logger,
)

from core.market.models import (
    MarketStatus,
)

from core.portfolio.models import (
    PortfolioAnalysis,
)

logger = get_logger(__name__)


# =====================================================
# PORTFOLIO MANAGER
# =====================================================

def portfolio_score(
    portfolio: PortfolioAnalysis,
) -> float:
    """
    Portfolio Manager score.
    """

    score = portfolio.health.score

    if portfolio.rebalance.needs_rebalance:
        score -= 10

    score -= portfolio.risk.score * 0.20

    return round(

        max(
            0,
            min(
                score,
                100,
            ),
        ),

        2,

    )


# =====================================================
# MARKET ANALYST
# =====================================================

def market_score(
    market: MarketStatus,
) -> float:
    """
    Market Analyst score.
    """

    return round(

        market.market_score,

        2,

    )


# =====================================================
# RISK MANAGER
# =====================================================

def risk_score(
    portfolio: PortfolioAnalysis,
) -> float:
    """
    Risk Manager score.
    """

    score = 100

    score -= portfolio.risk.score

    if portfolio.optimization.concentration_risk:

        score -= 10

    if portfolio.rebalance.needs_rebalance:

        score -= 10

    return round(

        max(
            0,
            min(
                score,
                100,
            ),
        ),

        2,

    )


# =====================================================
# AI ANALYST
# =====================================================

def ai_score(
    portfolio: PortfolioAnalysis,
    market: MarketStatus,
) -> float:
    """
    AI Analyst score.

    Average of portfolio and market.
    """

    return round(

        (

            portfolio_score(
                portfolio,
            )

            + market_score(
                market,
            )

        )

        / 2,

        2,

    )


# =====================================================
# COMMITTEE SCORECARD
# =====================================================

def generate_scorecard(
    portfolio: PortfolioAnalysis,
    market: MarketStatus,
) -> dict[str, float]:
    """
    Generate committee scorecard.
    """

    logger.info(
        "Generating committee scorecard..."
    )

    scorecard = {

        "portfolio": portfolio_score(
            portfolio,
        ),

        "market": market_score(
            market,
        ),

        "risk": risk_score(
            portfolio,
        ),

        "ai": ai_score(
            portfolio,
            market,
        ),

    }

    logger.info(
        "Committee scorecard ready."
    )

    return scorecard


# =====================================================
# EXPORTS
# =====================================================

__all__ = [

    "portfolio_score",

    "market_score",

    "risk_score",

    "ai_score",

    "generate_scorecard",

]