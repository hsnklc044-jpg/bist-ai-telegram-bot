"""
QuantBIST RC5
Market Intelligence Service
"""

from __future__ import annotations


from datetime import datetime


from core.infrastructure.exceptions import (
    MarketError,
)

from core.infrastructure.logger import (
    get_logger,
)

from core.market.breadth import (
    calculate_market_breadth,
)

from core.market.data import (
    load_snapshot,
)

from core.market.indicators import (
    generate_indicator_snapshot,
)

from core.market.models import (
    MarketStatus,
    VolatilityLevel,
)

from core.market.regime import (
    determine_market_regime,
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
# HELPERS
# =====================================================


def _volatility(
    snapshot,
) -> VolatilityLevel:
    """
    Calculate volatility level.
    """

    try:

        if snapshot.price <= 0:

            return VolatilityLevel.NORMAL



        ratio = (

            snapshot.atr

            /

            snapshot.price

        )



        if ratio >= 0.03:

            return VolatilityLevel.HIGH



        if ratio <= 0.01:

            return VolatilityLevel.LOW



        return VolatilityLevel.NORMAL



    except Exception:


        logger.exception(
            "Volatility calculation failed."
        )


        return VolatilityLevel.NORMAL





# =====================================================
# PUBLIC API
# =====================================================


def get_market_status(
    symbol: str = DEFAULT_MARKET_SYMBOL,
) -> MarketStatus:
    """
    Execute RC5 Market Intelligence Engine.

    Pipeline:

        Data
          ↓
        Indicators
          ↓
        Breadth
          ↓
        Sentiment
          ↓
        Regime
          ↓
        MarketStatus

    """

    logger.info(

        "Market Intelligence started | %s",

        symbol,

    )



    try:


        market = load_snapshot(

            symbol,

        )



        if not market:


            raise MarketError(

                f"Market snapshot unavailable: {symbol}"

            )





        indicators = generate_indicator_snapshot(

            symbol,

        )





        breadth = calculate_market_breadth(

            symbol,

        )





        sentiment = calculate_market_sentiment(

            symbol,

        )





        regime = determine_market_regime(

            symbol,

        )





        volatility = _volatility(

            indicators,

        )






        status = MarketStatus(



            status=regime.status.value,



            index=symbol,



            change=market.get(

                "change",

                0,

            ),



            trend=indicators.trend,



            volatility=volatility,



            breadth=breadth,



            sentiment=sentiment,



            regime=regime,



            indicators=indicators,



            updated=market.get(

                "updated",

                datetime.now(),

            ),



        )






        logger.info(

            "Market completed | "
            "Regime=%s | Score=%.2f | Volatility=%s",

            regime.status.value,

            status.market_score,

            volatility.value,

        )




        return status





    except MarketError:

        raise





    except Exception as exc:


        logger.exception(

            "Market Intelligence failed."

        )


        raise MarketError(

            str(exc)

        ) from exc





# =====================================================
# SHORTCUTS
# =====================================================


def market_score(
    market: MarketStatus,
) -> float:

    return market.market_score




def bullish(
    market: MarketStatus,
) -> bool:

    return market.bullish




def bearish(
    market: MarketStatus,
) -> bool:

    return market.bearish




def risk_on(
    market: MarketStatus,
) -> bool:

    return market.risk_on




def risk_off(
    market: MarketStatus,
) -> bool:

    return market.risk_off





# =====================================================
# EXPORTS
# =====================================================

__all__ = [

    "get_market_status",

    "market_score",

    "bullish",

    "bearish",

    "risk_on",

    "risk_off",

]
