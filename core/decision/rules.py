"""
QuantBIST Framework
Decision Rules Engine
"""

from __future__ import annotations

from dataclasses import dataclass

from core.market.models import MarketStatus
from core.portfolio.models import PortfolioAnalysis


# =====================================================
# CONSTANTS
# =====================================================

STRONG_BUY_SCORE = 90
BUY_SCORE = 75
HOLD_SCORE = 60
WATCH_SCORE = 45
REDUCE_SCORE = 30


# =====================================================
# RESULT MODEL
# =====================================================

@dataclass(slots=True)
class RuleResult:
    """
    Decision rule evaluation result.
    """

    action: str
    priority: str
    score: int


# =====================================================
# PORTFOLIO ADJUSTMENTS
# =====================================================

def _portfolio_health_adjustment(
    portfolio: PortfolioAnalysis,
) -> int:
    """
    Portfolio health adjustment.
    """

    score = portfolio.health.score

    if score >= 90:
        return 8

    if score >= 80:
        return 5

    if score >= 70:
        return 2

    if score >= 60:
        return 0

    return -8


def _portfolio_risk_adjustment(
    portfolio: PortfolioAnalysis,
) -> int:
    """
    Portfolio risk adjustment.
    """

    level = portfolio.risk.level.upper()

    mapping = {
        "LOW": 5,
        "MEDIUM": 0,
        "HIGH": -10,
        "CRITICAL": -20,
    }

    return mapping.get(level, 0)


def _optimization_adjustment(
    portfolio: PortfolioAnalysis,
) -> int:
    """
    Portfolio optimization adjustment.
    """

    optimization = portfolio.optimization

    adjustment = 0

    if optimization.concentration_risk:
        adjustment -= 10

    if optimization.rebalance:
        adjustment -= 5

    if hasattr(optimization, "health_score"):

        if optimization.health_score >= 90:
            adjustment += 5

        elif optimization.health_score < 60:
            adjustment -= 5

    return adjustment


# =====================================================
# MARKET ADJUSTMENTS
# =====================================================

def _market_regime_adjustment(
    market: MarketStatus,
) -> int:
    """
    Market regime adjustment.
    """

    regime = market.regime.status.upper()

    mapping = {
        "RISK_ON": 10,
        "NEUTRAL": 0,
        "RISK_OFF": -15,
    }

    return mapping.get(regime, 0)


def _market_breadth_adjustment(
    market: MarketStatus,
) -> int:
    """
    Market breadth adjustment.
    """

    status = market.breadth.status.upper()

    mapping = {
        "POSITIVE": 5,
        "NEUTRAL": 0,
        "NEGATIVE": -5,
    }

    return mapping.get(status, 0)


def _market_sentiment_adjustment(
    market: MarketStatus,
) -> int:
    """
    Market sentiment adjustment.
    """

    sentiment = market.sentiment.status.upper()

    mapping = {
        "GREED": 2,
        "NEUTRAL": 0,
        "FEAR": -5,
    }

    return mapping.get(sentiment, 0)


# =====================================================
# FINAL SCORE
# =====================================================

def calculate_decision_score(
    ai_score: int,
    portfolio: PortfolioAnalysis,
    market: MarketStatus,
) -> int:
    """
    Calculate final decision score.
    """

    score = ai_score

    score += _portfolio_health_adjustment(
        portfolio,
    )

    score += _portfolio_risk_adjustment(
        portfolio,
    )

    score += _optimization_adjustment(
        portfolio,
    )

    score += _market_regime_adjustment(
        market,
    )

    score += _market_breadth_adjustment(
        market,
    )

    score += _market_sentiment_adjustment(
        market,
    )

    return max(
        0,
        min(
            round(score),
            100,
        ),
    )


# =====================================================
# ACTION
# =====================================================

def determine_action(
    score: int,
) -> str:
    """
    Determine investment action.
    """

    if score >= STRONG_BUY_SCORE:
        return "STRONG BUY"

    if score >= BUY_SCORE:
        return "BUY"

    if score >= HOLD_SCORE:
        return "HOLD"

    if score >= WATCH_SCORE:
        return "WATCH"

    if score >= REDUCE_SCORE:
        return "REDUCE"

    return "SELL"


# =====================================================
# PRIORITY
# =====================================================

def determine_priority(
    score: int,
) -> str:
    """
    Determine execution priority.
    """

    if score >= STRONG_BUY_SCORE:
        return "LOW"

    if score >= BUY_SCORE:
        return "MEDIUM"

    if score >= HOLD_SCORE:
        return "HIGH"

    return "CRITICAL"


# =====================================================
# PUBLIC API
# =====================================================

def evaluate_rules(
    ai_score: int,
    portfolio: PortfolioAnalysis,
    market: MarketStatus,
) -> RuleResult:
    """
    Execute the complete decision rule engine.

    Parameters
    ----------
    ai_score
        AI scoring engine result.

    portfolio
        Portfolio analysis.

    market
        Market analysis.

    Returns
    -------
    RuleResult
    """

    final_score = calculate_decision_score(
        ai_score=ai_score,
        portfolio=portfolio,
        market=market,
    )

    action = determine_action(
        final_score,
    )

    priority = determine_priority(
        final_score,
    )

    return RuleResult(
        action=action,
        priority=priority,
        score=final_score,
    )
