"""
QuantBIST RC5
Market Regime Engine
"""

from __future__ import annotations


from core.infrastructure.exceptions import (
    MarketError,
)

from core.infrastructure.logger import (
    get_logger,
)

from core.market.breadth import (
    calculate_market_breadth,
)

from core.market.indicators import (
    generate_indicator_snapshot,
)

from core.market.models import (
    MarketRegime,
    MarketRegimeType,
    MarketTrend,
)

from core.market.sentiment import (
    calculate_market_sentiment,
)


logger = get_logger(__name__)



# =====================================================
# CONFIG
# =====================================================


DEFAULT_MARKET_SYMBOL = "XU100.IS"






# =====================================================
# SCORE HELPERS
# =====================================================


def _trend_score(
    trend: MarketTrend,
) -> float:
    """
    Trend contribution.
    """

    mapping = {

        MarketTrend.BULLISH:
            80.0,

        MarketTrend.NEUTRAL:
            50.0,

        MarketTrend.BEARISH:
            20.0,

    }


    return mapping.get(

        trend,

        50.0,

    )






def _normalize(
    score: float,
) -> float:

    return max(

        0.0,

        min(

            score,

            100.0,

        ),

    )





# =====================================================
# REGIME DECISION
# =====================================================


def _determine_regime(
    score: float,
) -> MarketRegimeType:
    """
    Convert score into market regime.
    """


    if score >= 70:

        return MarketRegimeType.RISK_ON



    if score >= 45:

        return MarketRegimeType.NEUTRAL



    return MarketRegimeType.RISK_OFF






# =====================================================
# PUBLIC API
# =====================================================


def determine_market_regime(
    symbol: str = DEFAULT_MARKET_SYMBOL,
) -> MarketRegime:
    """
    Determine current market regime.

    Pipeline:

    Trend
      +
    Breadth
      +
    Sentiment
      ↓
    Regime

    """


    logger.info(

        "Determining market regime | %s",

        symbol,

    )


    try:


        snapshot = generate_indicator_snapshot(

            symbol,

        )


        breadth = calculate_market_breadth(

            symbol,

        )


        sentiment = calculate_market_sentiment(

            symbol,

        )



        trend_score = _trend_score(

            snapshot.trend,

        )


        breadth_score = _normalize(

            breadth.score,

        )


        sentiment_score = _normalize(

            sentiment.score,

        )



        score = round(

            (

                trend_score * 0.40

                +

                breadth_score * 0.30

                +

                sentiment_score * 0.30

            ),

            2,

        )



        status = _determine_regime(

            score,

        )



        summary = (

            f"{status.value} "

            f"({score:.0f}/100)"

        )



        factors = {


            "trend":

                trend_score,


            "breadth":

                breadth_score,


            "sentiment":

                sentiment_score,


            "weights":

            {

                "trend":0.40,

                "breadth":0.30,

                "sentiment":0.30,

            },


        }



        logger.info(

            "Market regime completed | %s | %.2f",

            status.value,

            score,

        )



        return MarketRegime(

            status=status,

            score=score,

            summary=summary,

            factors=factors,

        )



    except Exception as exc:


        logger.exception(

            "Market regime calculation failed."

        )


        raise MarketError(

            str(exc)

        ) from exc






# =====================================================
# HELPERS
# =====================================================


def is_risk_on(
    regime: MarketRegime,
) -> bool:

    return regime.status is MarketRegimeType.RISK_ON




def is_risk_off(
    regime: MarketRegime,
) -> bool:

    return regime.status is MarketRegimeType.RISK_OFF




def is_neutral(
    regime: MarketRegime,
) -> bool:

    return regime.status is MarketRegimeType.NEUTRAL






# =====================================================
# EXPORTS
# =====================================================


__all__ = [

    "determine_market_regime",

    "is_risk_on",

    "is_risk_off",

    "is_neutral",

]
