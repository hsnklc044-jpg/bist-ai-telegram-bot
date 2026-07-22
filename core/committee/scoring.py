"""
QuantBIST RC5
Investment Committee Scoring Engine
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
# CONSTANTS
# =====================================================


MAX_SCORE = 100

MIN_SCORE = 0



REBALANCE_PENALTY = 8


CONCENTRATION_PENALTY = 10


RISK_WEIGHT = 0.15





# Committee weights

PORTFOLIO_WEIGHT = 0.35

MARKET_WEIGHT = 0.35

RISK_WEIGHT_FINAL = 0.30





# =====================================================
# HELPERS
# =====================================================


def _normalize_score(
    score: float,
) -> float:
    """
    Keep score between 0-100.
    """


    return round(

        max(

            MIN_SCORE,

            min(

                MAX_SCORE,

                float(score),

            ),

        ),

        2,

    )






# =====================================================
# PORTFOLIO MANAGER
# =====================================================


def portfolio_score(
    portfolio: PortfolioAnalysis,
) -> float:
    """
    Portfolio Manager evaluation.
    """


    score = float(

        portfolio.health.score

    )



    if portfolio.rebalance.needs_rebalance:

        score -= REBALANCE_PENALTY



    risk_penalty = (

        portfolio.risk.score

        *

        RISK_WEIGHT

    )



    score -= risk_penalty



    return _normalize_score(

        score

    )







# =====================================================
# MARKET ANALYST
# =====================================================


def market_score(
    market: MarketStatus,
) -> float:
    """
    Market Analyst evaluation.
    """


    if market is None:

        return 50.0



    return _normalize_score(

        market.market_score

    )







# =====================================================
# RISK MANAGER
# =====================================================


def risk_score(
    portfolio: PortfolioAnalysis,
) -> float:
    """
    Risk Manager evaluation.

    Lower risk = higher score.
    """


    if portfolio is None:

        return 50.0



    risk = float(

        portfolio.risk.score

    )



    score = 100 - risk



    if portfolio.optimization.concentration_risk:

        score -= CONCENTRATION_PENALTY



    if portfolio.rebalance.needs_rebalance:

        score -= REBALANCE_PENALTY



    return _normalize_score(

        score

    )







# =====================================================
# AI ANALYST
# =====================================================


def ai_score(
    portfolio: PortfolioAnalysis,
    market: MarketStatus,
) -> float:
    """
    AI Analyst intelligence score.

    Highest committee influence.
    """


    portfolio_value = portfolio_score(

        portfolio

    )


    market_value = market_score(

        market

    )


    risk_value = risk_score(

        portfolio

    )



    score = (

        portfolio_value

        *

        PORTFOLIO_WEIGHT

        +

        market_value

        *

        MARKET_WEIGHT

        +

        risk_value

        *

        RISK_WEIGHT_FINAL

    )



    return _normalize_score(

        score

    )







# =====================================================
# SCORECARD
# =====================================================


def generate_scorecard(
    portfolio: PortfolioAnalysis,
    market: MarketStatus,
) -> dict[str, float]:
    """
    Generate committee intelligence scorecard.
    """


    logger.info(

        "Generating committee scorecard."

    )



    scorecard = {


        "portfolio":

            portfolio_score(

                portfolio,

            ),



        "market":

            market_score(

                market,

            ),



        "risk":

            risk_score(

                portfolio,

            ),



        "ai":

            ai_score(

                portfolio,

                market,

            ),


    }



    logger.info(

        "Committee scorecard ready | %s",

        scorecard,

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