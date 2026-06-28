"""
QuantBIST Framework
AI Recommendation Engine
"""

from __future__ import annotations

from core.ai.scoring import calculate_score
from core.decision.models import Decision
from core.infrastructure.logger import get_logger
from core.market.models import MarketStatus
from core.portfolio.models import PortfolioAnalysis

logger = get_logger(__name__)


def generate_recommendation(
    portfolio: PortfolioAnalysis,
    market: MarketStatus,
) -> Decision:
    """
    Generate the final investment recommendation.

    Parameters
    ----------
    portfolio
        Portfolio analysis.

    market
        Market analysis.

    Returns
    -------
    Decision
    """

    logger.info(
        "Generating AI recommendation..."
    )

    # --------------------------------------------------
    # AI SCORE
    # --------------------------------------------------

    score = calculate_score(
        portfolio,
        market,
    )

    # --------------------------------------------------
    # ACTION
    # --------------------------------------------------

    if score >= 90:

        action = "STRONG BUY"

    elif score >= 75:

        action = "BUY"

    elif score >= 55:

        action = "WATCH"

    elif score >= 35:

        action = "REDUCE"

    else:

        action = "SELL"

    # --------------------------------------------------
    # CONFIDENCE
    # --------------------------------------------------

    confidence = min(
        99,
        max(
            50,
            score + 5,
        ),
    )

    # --------------------------------------------------
    # REASON
    # --------------------------------------------------

    reasons = []

    if portfolio.health.grade == "A":
        reasons.append(
            "Healthy portfolio"
        )

    elif portfolio.health.grade == "B":
        reasons.append(
            "Stable portfolio"
        )

    else:
        reasons.append(
            "Portfolio needs improvement"
        )

    if market.regime == "RISK_ON":

        reasons.append(
            "Risk-On market"
        )

    elif market.regime == "RISK_OFF":

        reasons.append(
            "Risk-Off market"
        )

    else:

        reasons.append(
            "Neutral market"
        )

    if portfolio.rebalance.needs_rebalance:

        reasons.append(
            "Portfolio rebalancing recommended"
        )

    reason = ". ".join(reasons)

    # --------------------------------------------------
    # RESULT
    # --------------------------------------------------

    decision = Decision(

        action=action,

        score=score,

        confidence=confidence,

        reason=reason,

    )

    logger.info(

        "Recommendation: %s (%d)",

        action,

        score,

    )

    return decision