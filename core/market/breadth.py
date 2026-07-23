"""
QuantBIST RC5
Market Breadth Engine
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
    BreadthStatus,
    MarketBreadth,
    MarketTrend,
)


logger = get_logger(__name__)




# =====================================================
# DEFAULT MARKET SYMBOL
# =====================================================

DEFAULT_MARKET_SYMBOL = "XU100.IS"





# =====================================================
# SCORE HELPERS
# =====================================================


def _trend_score(
    snapshot,
) -> float:
    """
    Trend contribution.
    """

    if snapshot.trend is MarketTrend.BULLISH:

        return 35.0


    if snapshot.trend is MarketTrend.NEUTRAL:

        return 20.0


    return 5.0





def _rsi_score(
    snapshot,
) -> float:
    """
    RSI contribution.
    """

    if 45 <= snapshot.rsi <= 65:

        return 25.0


    if 35 <= snapshot.rsi <= 75:

        return 15.0


    return 5.0





def _macd_score(
    snapshot,
) -> float:
    """
    MACD contribution.
    """

    if snapshot.macd > snapshot.macd_signal:

        return 20.0


    return 5.0





def _ema_score(
    snapshot,
) -> float:
    """
    Long term trend contribution.
    """

    if snapshot.price > snapshot.ema200:

        return 20.0


    return 5.0





# =====================================================
# STATUS
# =====================================================


def _breadth_status(
    score: float,
) -> BreadthStatus:
    """
    Convert score into breadth status.
    """

    if score >= 70:

        return BreadthStatus.POSITIVE



    if score >= 45:

        return BreadthStatus.NEUTRAL



    return BreadthStatus.NEGATIVE





# =====================================================
# PUBLIC API
# =====================================================


def calculate_market_breadth(
    symbol: str = DEFAULT_MARKET_SYMBOL,
) -> MarketBreadth:
    """
    Calculate overall market breadth.

    Pipeline:

        Indicators
             ↓
        Breadth Score
             ↓
        Breadth Status

    """

    logger.info(

        "Calculating market breadth | %s",

        symbol,

    )


    try:


        snapshot = generate_indicator_snapshot(

            symbol,

        )



        trend = _trend_score(

            snapshot,

        )


        rsi = _rsi_score(

            snapshot,

        )


        macd = _macd_score(

            snapshot,

        )


        ema = _ema_score(

            snapshot,

        )




        score = round(

            trend

            +

            rsi

            +

            macd

            +

            ema,

            2,

        )



        score = min(

            max(

                score,

                0.0,

            ),

            100.0,

        )




        status = _breadth_status(

            score,

        )





        factors = {

            "trend":

                trend,


            "rsi":

                rsi,


            "macd":

                macd,


            "ema":

                ema,

        }





        summary = (

            f"{status.value} breadth "

            f"({score:.0f}/100)"

        )





        logger.info(

            "Market breadth completed | Score=%.2f",

            score,

        )





        return MarketBreadth(

            status=status,

            score=score,

            summary=summary,

            factors=factors,

        )





    except Exception as exc:


        logger.exception(

            "Market breadth calculation failed."

        )


        raise MarketError(

            str(exc)

        ) from exc





# =====================================================
# EXPORTS
# =====================================================

__all__ = [

    "calculate_market_breadth",

]
