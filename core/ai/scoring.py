"""
QuantBIST Framework
AI Scoring Engine
"""

from __future__ import annotations

from core.config.ai import (
    BASE_SCORE,
    BREADTH_NEGATIVE_SCORE,
    BREADTH_NEUTRAL_SCORE,
    BREADTH_POSITIVE_SCORE,
    CRITICAL_RISK_SCORE,
    FEAR_SCORE,
    GRADE_A_SCORE,
    GRADE_B_SCORE,
    GRADE_C_SCORE,
    GRADE_D_SCORE,
    GREED_SCORE,
    HIGH_RISK_SCORE,
    LOW_RISK_SCORE,
    MARKET_NEUTRAL_SCORE,
    MAX_SCORE,
    MEDIUM_RISK_SCORE,
    MIN_SCORE,
    NO_REBALANCE_BONUS,
    REBALANCE_PENALTY,
    RISK_OFF_SCORE,
    RISK_ON_SCORE,
)

from core.infrastructure.logger import get_logger
from core.market.models import MarketStatus
from core.portfolio.models import PortfolioAnalysis

logger = get_logger(__name__)


# =====================================================
# HELPERS
# =====================================================

def _clamp(score: int) -> int:
    """
    Clamp score into configured range.
    """

    return max(
        MIN_SCORE,
        min(
            MAX_SCORE,
            score,
        ),
    )


# =====================================================
# PORTFOLIO
# =====================================================

def _portfolio_grade_score(
    portfolio: PortfolioAnalysis,
) -> int:
    """
    Portfolio grade contribution.
    """

    grade = portfolio.health.grade.upper()

    mapping = {

        "A": GRADE_A_SCORE,

        "B": GRADE_B_SCORE,

        "C": GRADE_C_SCORE,

        "D": GRADE_D_SCORE,

    }

    return mapping.get(
        grade,
        0,
    )


def _portfolio_risk_score(
    portfolio: PortfolioAnalysis,
) -> int:
    """
    Portfolio risk contribution.
    """

    level = portfolio.risk.level.upper()

    mapping = {

        "LOW": LOW_RISK_SCORE,

        "MEDIUM": MEDIUM_RISK_SCORE,

        "HIGH": HIGH_RISK_SCORE,

        "CRITICAL": CRITICAL_RISK_SCORE,

    }

    return mapping.get(
        level,
        0,
    )


def _rebalance_score(
    portfolio: PortfolioAnalysis,
) -> int:
    """
    Rebalance contribution.
    """

    if portfolio.rebalance.needs_rebalance:

        return REBALANCE_PENALTY

    return NO_REBALANCE_BONUS


def calculate_portfolio_score(
    portfolio: PortfolioAnalysis,
) -> int:
    """
    Calculate portfolio contribution.
    """

    score = 0

    score += _portfolio_grade_score(
        portfolio,
    )

    score += _portfolio_risk_score(
        portfolio,
    )

    score += _rebalance_score(
        portfolio,
    )

    return score


# =====================================================
# MARKET
# =====================================================

def _market_regime_score(
    market: MarketStatus,
) -> int:
    """
    Market regime contribution.
    """

    regime = market.regime.status.upper()

    mapping = {

        "RISK_ON": RISK_ON_SCORE,

        "NEUTRAL": MARKET_NEUTRAL_SCORE,

        "RISK_OFF": RISK_OFF_SCORE,

    }

    return mapping.get(
        regime,
        0,
    )


def _market_breadth_score(
    market: MarketStatus,
) -> int:
    """
    Market breadth contribution.
    """

    breadth = market.breadth.status.upper()

    mapping = {

        "POSITIVE": BREADTH_POSITIVE_SCORE,

        "NEUTRAL": BREADTH_NEUTRAL_SCORE,

        "NEGATIVE": BREADTH_NEGATIVE_SCORE,

    }

    return mapping.get(
        breadth,
        0,
    )


def _market_sentiment_score(
    market: MarketStatus,
) -> int:
    """
    Market sentiment contribution.
    """

    sentiment = market.sentiment.status.upper()

    mapping = {

        "GREED": GREED_SCORE,

        "NEUTRAL": 0,

        "FEAR": FEAR_SCORE,

    }

    return mapping.get(
        sentiment,
        0,
    )


def calculate_market_score(
    market: MarketStatus,
) -> int:
    """
    Calculate market contribution.
    """

    score = 0

    score += _market_regime_score(
        market,
    )

    score += _market_breadth_score(
        market,
    )

    score += _market_sentiment_score(
        market,
    )

    return score


# =====================================================
# PUBLIC API
# =====================================================

def calculate_score(
    portfolio: PortfolioAnalysis,
    market: MarketStatus,
) -> int:
    """
    Calculate final AI score.

    Parameters
    ----------
    portfolio
        Portfolio analysis.

    market
        Market analysis.

    Returns
    -------
    int
        AI score between 0 and 100.
    """

    logger.info(
        "Calculating AI score..."
    )

    portfolio_score = calculate_portfolio_score(
        portfolio,
    )

    market_score = calculate_market_score(
        market,
    )

    score = (
        BASE_SCORE
        + portfolio_score
        + market_score
    )

    score = _clamp(
        score,
    )

    logger.info(

        "AI Score=%d | Portfolio=%d | Market=%d",

        score,

        portfolio_score,

        market_score,

    )

    return score


# =====================================================
# EXPORTS
# =====================================================

__all__ = [

    "calculate_score",

    "calculate_portfolio_score",

    "calculate_market_score",

]