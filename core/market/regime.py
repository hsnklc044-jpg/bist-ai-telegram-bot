"""
QuantBIST Framework
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
# DEFAULT MARKET SYMBOL
# =====================================================

DEFAULT_MARKET_SYMBOL = "^XU100.IS"


# =====================================================
# SCORE HELPERS
# =====================================================

def _trend_score(
    trend: MarketTrend,
) -> int:
    """
    Trend contribution.
    """

    if trend is MarketTrend.BULLISH:
        return 40

    if trend is MarketTrend.NEUTRAL:
        return 20

    return 0


# =====================================================
# PUBLIC API
# =====================================================

def determine_market_regime(
    symbol: str = DEFAULT_MARKET_SYMBOL,
) -> MarketRegime:
    """
    Determine current market regime.
    """

    logger.info(
        "Determining market regime..."
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

        score = (

            _trend_score(
                snapshot.trend,
            )

            + breadth.score * 0.30

            + sentiment.score * 0.30

        )

        score = round(

            min(
                score,
                100,
            ),

            2,

        )

        if score >= 70:

            status = MarketRegimeType.RISK_ON

        elif score >= 45:

            status = MarketRegimeType.NEUTRAL

        else:

            status = MarketRegimeType.RISK_OFF

        summary = (

            f"{status.value} "

            f"({score:.0f}/100)"

        )

        logger.info(

            "Market regime determined: %s",

            status.value,

        )

        return MarketRegime(

            status=status,

            score=score,

            summary=summary,

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
    """
    Returns True if market is Risk-On.
    """

    return regime.status is MarketRegimeType.RISK_ON


def is_risk_off(
    regime: MarketRegime,
) -> bool:
    """
    Returns True if market is Risk-Off.
    """

    return regime.status is MarketRegimeType.RISK_OFF


def is_neutral(
    regime: MarketRegime,
) -> bool:
    """
    Returns True if market is Neutral.
    """

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