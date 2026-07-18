"""
QuantBIST Framework
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
)

logger = get_logger(__name__)


# =====================================================
# DEFAULT MARKET SYMBOL
# =====================================================

DEFAULT_MARKET_SYMBOL = "^XU100.IS"


# =====================================================
# SCORE HELPERS
# =====================================================

def _trend_score(
    snapshot,
) -> int:
    """
    Trend contribution.
    """

    if snapshot.trend.value == "BULLISH":
        return 35

    if snapshot.trend.value == "NEUTRAL":
        return 20

    return 5


def _rsi_score(
    snapshot,
) -> int:
    """
    RSI contribution.
    """

    if 45 <= snapshot.rsi <= 65:
        return 25

    if 35 <= snapshot.rsi <= 75:
        return 15

    return 5


def _macd_score(
    snapshot,
) -> int:
    """
    MACD contribution.
    """

    if snapshot.macd > snapshot.macd_signal:
        return 20

    return 5


def _ema_score(
    snapshot,
) -> int:
    """
    EMA contribution.
    """

    if snapshot.price > snapshot.ema200:
        return 20

    return 5


# =====================================================
# PUBLIC API
# =====================================================

def calculate_market_breadth(
    symbol: str = DEFAULT_MARKET_SYMBOL,
) -> MarketBreadth:
    """
    Calculate overall market breadth.
    """

    logger.info(
        "Calculating market breadth..."
    )

    try:

        snapshot = generate_indicator_snapshot(
            symbol,
        )

        score = (

            _trend_score(snapshot)

            + _rsi_score(snapshot)

            + _macd_score(snapshot)

            + _ema_score(snapshot)

        )

        score = round(
            min(score, 100),
            2,
        )

        if score >= 70:

            status = BreadthStatus.POSITIVE

        elif score >= 45:

            status = BreadthStatus.NEUTRAL

        else:

            status = BreadthStatus.NEGATIVE

        summary = (
            f"{status.value} breadth "
            f"({score:.0f}/100)"
        )

        logger.info(
            "Market breadth calculated."
        )

        return MarketBreadth(

            status=status,

            score=score,

            summary=summary,

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