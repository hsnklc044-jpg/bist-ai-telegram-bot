"""
QuantBIST Framework
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

DEFAULT_MARKET_SYMBOL = "^XU100.IS"


# =====================================================
# SCORE HELPERS
# =====================================================

def _rsi_score(
    snapshot,
) -> int:
    """
    RSI contribution.
    """

    if snapshot.rsi >= 70:
        return 10

    if snapshot.rsi <= 30:
        return 90

    return 50


def _macd_score(
    snapshot,
) -> int:
    """
    MACD contribution.
    """

    if snapshot.macd > snapshot.macd_signal:
        return 70

    return 30


def _momentum_score(
    snapshot,
) -> int:
    """
    Momentum contribution.
    """

    mapping = {

        "POSITIVE": 80,

        "NEUTRAL": 50,

        "NEGATIVE": 20,

        "OVERBOUGHT": 35,

        "OVERSOLD": 75,

    }

    return mapping.get(
        snapshot.momentum,
        50,
    )


# =====================================================
# PUBLIC API
# =====================================================

def calculate_market_sentiment(
    symbol: str = DEFAULT_MARKET_SYMBOL,
) -> MarketSentiment:
    """
    Calculate market sentiment.
    """

    logger.info(
        "Calculating market sentiment..."
    )

    try:

        snapshot = generate_indicator_snapshot(
            symbol,
        )

        score = round(

            (

                _rsi_score(snapshot)

                + _macd_score(snapshot)

                + _momentum_score(snapshot)

            )

            / 3,

            2,

        )

        if score >= 70:

            status = SentimentStatus.GREED

        elif score >= 45:

            status = SentimentStatus.NEUTRAL

        else:

            status = SentimentStatus.FEAR

        summary = (

            f"{status.value} sentiment "

            f"({score:.0f}/100)"

        )

        logger.info(
            "Market sentiment calculated."
        )

        return MarketSentiment(

            status=status,

            score=score,

            summary=summary,

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