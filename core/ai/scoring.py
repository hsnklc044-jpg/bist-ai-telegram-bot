"""
QuantBIST Framework
AI Scoring Engine
"""

from __future__ import annotations

from core.market.models import MarketStatus
from core.portfolio.models import PortfolioAnalysis


def score_portfolio(
    portfolio: PortfolioAnalysis,
) -> int:
    """
    Score portfolio quality.
    """

    score = 0

    grade = portfolio.health.grade.upper()

    if grade == "A":
        score += 25

    elif grade == "B":
        score += 15

    elif grade == "C":
        score += 5

    risk = portfolio.risk.level.upper()

    if risk == "LOW":
        score += 20

    elif risk == "MEDIUM":
        score += 10

    elif risk == "HIGH":
        score -= 10

    elif risk == "CRITICAL":
        score -= 20

    if portfolio.rebalance.needs_rebalance:
        score -= 5
    else:
        score += 5

    return score


def score_market(
    market: MarketStatus,
) -> int:
    """
    Score market conditions.
    """

    score = 0

    if market.regime.status == "RISK_ON":
        score += 25

    elif market.regime.status == "NEUTRAL":
        score += 10

    else:
        score -= 20

    if market.breadth.status == "POSITIVE":
        score += 10

    elif market.breadth.status == "NEUTRAL":
        score += 5

    else:
        score -= 10

    if market.sentiment.status == "GREED":
        score += 10

    elif market.sentiment.status == "FEAR":
        score -= 10

    return score


def clamp_score(
    score: int,
) -> int:
    """
    Clamp score to the range 0-100.
    """

    return max(
        0,
        min(
            100,
            score,
        ),
    )


def calculate_score(
    portfolio: PortfolioAnalysis,
    market: MarketStatus,
) -> int:
    """
    Calculate final AI score.
    """

    total = 50

    total += score_portfolio(
        portfolio,
    )

    total += score_market(
        market,
    )

    return clamp_score(
        total,
    )