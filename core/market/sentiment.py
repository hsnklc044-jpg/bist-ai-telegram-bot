"""
QuantBIST RC5
Market Sentiment Engine
"""

from __future__ import annotations

from core.infrastructure.exceptions import (
    MarketError,
)
from core.infrastructure.logger import (
    get_logger,
)
from core.market.indicators import (
    generate_indicator_snapshot,
)
from core.market.models import (
    MarketSentiment,
    SentimentStatus,
)

logger = get_logger(__name__)




# =====================================================
# DEFAULT MARKET SYMBOL
# =====================================================

DEFAULT_MARKET_SYMBOL = "XU100.IS"





# =====================================================
# SCORE HELPERS
# =====================================================


def _rsi_score(
    snapshot,
) -> float:
    """
    RSI sentiment contribution.

    Extreme fear creates opportunity.
    """

    if snapshot.rsi <= 30:

        return 90.0



    if snapshot.rsi < 40:

        return 75.0



    if snapshot.rsi >= 70:

        return 20.0



    if snapshot.rsi > 60:

        return 40.0



    return 60.0





def _macd_score(
    snapshot,
) -> float:
    """
    MACD sentiment contribution.
    """

    if snapshot.macd > snapshot.macd_signal:

        return 75.0



    return 30.0





def _momentum_score(
    snapshot,
) -> float:
    """
    Momentum sentiment contribution.
    """

    mapping = {

        "POSITIVE": 80.0,

        "NEUTRAL": 50.0,

        "NEGATIVE": 20.0,

        "OVERBOUGHT": 35.0,

        "OVERSOLD": 75.0,

    }


    return mapping.get(

        snapshot.momentum,

        50.0,

    )





# =====================================================
# STATUS
# =====================================================


def _sentiment_status(
    score: float,
) -> SentimentStatus:
    """
    Convert score into sentiment status.
    """

    if score >= 70:

        return SentimentStatus.GREED



    if score >= 45:

        return SentimentStatus.NEUTRAL



    return SentimentStatus.FEAR





# =====================================================
# PUBLIC API
# =====================================================


def calculate_market_sentiment(
    symbol: str = DEFAULT_MARKET_SYMBOL,
) -> MarketSentiment:
    """
    Calculate market sentiment.

    Pipeline:

        Indicators
             ↓
        Sentiment Score
             ↓
        Sentiment Status

    """

    logger.info(

        "Calculating market sentiment | %s",

        symbol,

    )


    try:


        snapshot = generate_indicator_snapshot(

            symbol,

        )



        rsi = _rsi_score(

            snapshot,

        )


        macd = _macd_score(

            snapshot,

        )


        momentum = _momentum_score(

            snapshot,

        )





        score = round(

            (

                rsi * 0.40

                +

                macd * 0.30

                +

                momentum * 0.30

            ),

            2,

        )





        status = _sentiment_status(

            score,

        )





        factors = {

            "rsi":

                rsi,


            "macd":

                macd,


            "momentum":

                momentum,

        }





        summary = (

            f"{status.value} sentiment "

            f"({score:.0f}/100)"

        )





        logger.info(

            "Market sentiment completed | Score=%.2f",

            score,

        )





        return MarketSentiment(

            status=status,

            score=score,

            summary=summary,

            factors=factors,

        )





    except Exception as exc:


        logger.exception(

            "Market sentiment calculation failed."

        )


        raise MarketError(

            str(exc)

        ) from exc





# =====================================================
# EXPORTS
# =====================================================

__all__ = [

    "calculate_market_sentiment",

]
