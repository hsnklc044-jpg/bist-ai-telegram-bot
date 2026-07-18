"""
QuantBIST Framework
Market Service
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

def _volatility(snapshot) -> VolatilityLevel:
    """
    Estimate volatility from ATR ratio.
    """

    if snapshot.price <= 0:
        return VolatilityLevel.NORMAL

    ratio = snapshot.atr / snapshot.price

    if ratio >= 0.03:
        return VolatilityLevel.HIGH

    if ratio <= 0.01:
        return VolatilityLevel.LOW

    return VolatilityLevel.NORMAL


# =====================================================
# PUBLIC API
# =====================================================

def get_market_status(
    symbol: str = DEFAULT_MARKET_SYMBOL,
) -> MarketStatus:
    """
    Execute complete Market Engine.

    Returns
    -------
    MarketStatus
    """

    logger.info(
        "Market Service started."
    )

    try:

        market = load_snapshot(
            symbol,
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

        status = MarketStatus(

            status=regime.status.value,

            index=symbol,

            change=market["change"],

            trend=indicators.trend,

            volatility=_volatility(
                indicators,
            ),

            breadth=breadth,

            sentiment=sentiment,

            regime=regime,

            indicators=indicators,

            updated=market["updated"],

        )

        logger.info(
            "Market Service completed."
        )

        return status

    except MarketError:

        raise

    except Exception as exc:

        logger.exception(
            "Market Service failed."
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
    """
    Return composite market score.
    """

    return market.market_score


def bullish(
    market: MarketStatus,
) -> bool:
    """
    Bullish market?
    """

    return market.bullish


def bearish(
    market: MarketStatus,
) -> bool:
    """
    Bearish market?
    """

    return market.bearish


def risk_on(
    market: MarketStatus,
) -> bool:
    """
    Risk-On market?
    """

    return market.risk_on


def risk_off(
    market: MarketStatus,
) -> bool:
    """
    Risk-Off market?
    """

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