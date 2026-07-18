"""
QuantBIST Framework
Decision Confidence Engine
"""

from __future__ import annotations

from core.market.models import MarketStatus
from core.portfolio.models import PortfolioAnalysis


# =====================================================
# WEIGHTS
# =====================================================

AI_WEIGHT = 0.30
HEALTH_WEIGHT = 0.25
RISK_WEIGHT = 0.20
MARKET_WEIGHT = 0.15
OPTIMIZATION_WEIGHT = 0.10


# =====================================================
# HEALTH
# =====================================================

def _health_component(
    portfolio: PortfolioAnalysis,
) -> float:
    """
    Portfolio health contribution.
    """

    return max(
        0.0,
        min(
            float(portfolio.health.score),
            100.0,
        ),
    )


# =====================================================
# RISK
# =====================================================

def _risk_component(
    portfolio: PortfolioAnalysis,
) -> float:
    """
    Portfolio risk contribution.

    Higher value means higher confidence.
    """

    mapping = {

        "LOW": 100.0,

        "MEDIUM": 80.0,

        "HIGH": 55.0,

        "CRITICAL": 30.0,

    }

    return mapping.get(

        portfolio.risk.level.upper(),

        60.0,

    )


# =====================================================
# MARKET
# =====================================================

def _market_component(
    market: MarketStatus,
) -> float:
    """
    Market confidence contribution.
    """

    score = 50.0

    regime = market.regime.status.upper()

    if regime == "RISK_ON":
        score += 25

    elif regime == "RISK_OFF":
        score -= 20

    breadth = market.breadth.status.upper()

    if breadth == "POSITIVE":
        score += 15

    elif breadth == "NEGATIVE":
        score -= 10

    sentiment = market.sentiment.status.upper()

    if sentiment == "GREED":
        score += 5

    elif sentiment == "FEAR":
        score -= 10

    return max(
        0.0,
        min(score, 100.0),
    )


# =====================================================
# OPTIMIZATION
# =====================================================

def _optimization_component(
    portfolio: PortfolioAnalysis,
) -> float:
    """
    Portfolio optimization contribution.
    """

    optimization = portfolio.optimization

    score = 100.0

    if optimization.concentration_risk:
        score -= 20

    if optimization.rebalance:
        score -= 15

    if hasattr(
        optimization,
        "health_score",
    ):

        score = (
            score
            + optimization.health_score
        ) / 2

    return max(
        0.0,
        min(score, 100.0),
    )


# =====================================================
# CONFIDENCE
# =====================================================

def calculate_confidence(
    ai_score: int,
    portfolio: PortfolioAnalysis,
    market: MarketStatus,
) -> int:
    """
    Calculate final decision confidence.

    Components

    ----------
    AI Score

    Portfolio Health

    Portfolio Risk

    Market

    Portfolio Optimization
    """

    confidence = (

        ai_score * AI_WEIGHT

        + _health_component(
            portfolio,
        ) * HEALTH_WEIGHT

        + _risk_component(
            portfolio,
        ) * RISK_WEIGHT

        + _market_component(
            market,
        ) * MARKET_WEIGHT

        + _optimization_component(
            portfolio,
        ) * OPTIMIZATION_WEIGHT

    )

    return max(

        0,

        min(

            round(confidence),

            100,

        ),

    )


# =====================================================
# LABEL
# =====================================================

def confidence_label(
    confidence: int,
) -> str:
    """
    Human-readable confidence level.
    """

    if confidence >= 90:
        return "VERY HIGH"

    if confidence >= 80:
        return "HIGH"

    if confidence >= 65:
        return "MEDIUM"

    if confidence >= 50:
        return "LOW"

    return "VERY LOW"


# =====================================================
# BOOLEAN HELPERS
# =====================================================

def is_high_confidence(
    confidence: int,
) -> bool:
    """
    True if confidence is considered high.
    """

    return confidence >= 80


def is_medium_confidence(
    confidence: int,
) -> bool:
    """
    True if confidence is considered medium.
    """

    return 60 <= confidence < 80


def is_low_confidence(
    confidence: int,
) -> bool:
    """
    True if confidence is considered low.
    """

    return confidence < 60