"""
QuantBIST Framework
Decision Engine
"""

from __future__ import annotations

from core.ai.recommendation_engine import generate_recommendation
from core.decision.models import Decision
from core.infrastructure.exceptions import DecisionError
from core.infrastructure.logger import get_logger
from core.market.service import get_market_status
from core.portfolio.models import PortfolioStats
from core.portfolio.service import get_portfolio_analysis

logger = get_logger(__name__)


def generate_decision(
    stats: PortfolioStats,
) -> Decision:
    """
    Execute the complete decision workflow.
    """

    logger.info("Decision Engine started.")

    try:

        # ---------------------------------------------
        # Portfolio Engine
        # ---------------------------------------------

        portfolio = get_portfolio_analysis(
            stats,
        )

        # ---------------------------------------------
        # Market Engine
        # ---------------------------------------------

        market = get_market_status()

        # ---------------------------------------------
        # AI Recommendation Engine
        # ---------------------------------------------

        decision = generate_recommendation(

            portfolio=portfolio,

            market=market,

        )

        logger.info(
            "Decision Engine completed."
        )

        return decision

    except DecisionError:
        raise

    except Exception as exc:

        logger.exception(
            "Decision Engine failed."
        )

        raise DecisionError(
            str(exc)
        ) from exc