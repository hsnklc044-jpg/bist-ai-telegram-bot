"""
QuantBIST RC5
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


def _clamp(
    score: int,
) -> int:
    """
    Keep score between 0-100.
    """

    return max(

        MIN_SCORE,

        min(

            MAX_SCORE,

            score,

        ),

    )






# =====================================================
# PORTFOLIO SCORE
# =====================================================


def _portfolio_grade_score(
    portfolio: PortfolioAnalysis,
) -> int:


    mapping = {

        "A": GRADE_A_SCORE,

        "B": GRADE_B_SCORE,

        "C": GRADE_C_SCORE,

        "D": GRADE_D_SCORE,

    }


    return mapping.get(

        portfolio.health.grade.upper(),

        0,

    )





def _portfolio_risk_score(
    portfolio: PortfolioAnalysis,
) -> int:


    mapping = {

        "LOW":
            LOW_RISK_SCORE,


        "MEDIUM":
            MEDIUM_RISK_SCORE,


        "HIGH":
            HIGH_RISK_SCORE,


        "VERY_HIGH":
            CRITICAL_RISK_SCORE,


        "CRITICAL":
            CRITICAL_RISK_SCORE,

    }


    return mapping.get(

        portfolio.risk.level.upper(),

        0,

    )





def _rebalance_score(
    portfolio: PortfolioAnalysis,
) -> int:


    if portfolio.rebalance.needs_rebalance:

        return REBALANCE_PENALTY


    return NO_REBALANCE_BONUS





def calculate_portfolio_score(
    portfolio: PortfolioAnalysis,
) -> int:


    return (

        _portfolio_grade_score(
            portfolio
        )

        +

        _portfolio_risk_score(
            portfolio
        )

        +

        _rebalance_score(
            portfolio
        )

    )







# =====================================================
# MARKET SCORE
# =====================================================


def _market_regime_score(
    market: MarketStatus,
) -> int:


    mapping = {

        "RISK_ON":
            RISK_ON_SCORE,


        "NEUTRAL":
            MARKET_NEUTRAL_SCORE,


        "RISK_OFF":
            RISK_OFF_SCORE,

    }


    return mapping.get(

        market.regime.status.value.upper(),

        0,

    )





def _market_breadth_score(
    market: MarketStatus,
) -> int:


    mapping = {

        "POSITIVE":
            BREADTH_POSITIVE_SCORE,


        "NEUTRAL":
            BREADTH_NEUTRAL_SCORE,


        "NEGATIVE":
            BREADTH_NEGATIVE_SCORE,

    }


    return mapping.get(

        market.breadth.status.value.upper(),

        0,

    )





def _market_sentiment_score(
    market: MarketStatus,
) -> int:


    mapping = {

        "GREED":
            GREED_SCORE,


        "NEUTRAL":
            MARKET_NEUTRAL_SCORE,


        "FEAR":
            FEAR_SCORE,

    }


    return mapping.get(

        market.sentiment.status.value.upper(),

        0,

    )





def calculate_market_score(
    market: MarketStatus,
) -> int:


    return (

        _market_regime_score(
            market
        )

        +

        _market_breadth_score(
            market
        )

        +

        _market_sentiment_score(
            market
        )

    )






# =====================================================
# PUBLIC API
# =====================================================


def calculate_score(
    portfolio: PortfolioAnalysis,
    market: MarketStatus,
) -> int:
    """
    Final AI investment score.
    """


    logger.info(

        "AI scoring started."

    )


    portfolio_value = calculate_portfolio_score(

        portfolio,

    )


    market_value = calculate_market_score(

        market,

    )



    final_score = (

        BASE_SCORE

        +

        portfolio_value

        +

        market_value

    )



    final_score = _clamp(

        final_score,

    )



    logger.info(

        "AI Score=%d Portfolio=%d Market=%d",

        final_score,

        portfolio_value,

        market_value,

    )



    return final_score





# =====================================================
# EXPORTS
# =====================================================


__all__ = [

    "calculate_score",

    "calculate_portfolio_score",

    "calculate_market_score",

]
