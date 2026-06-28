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

from core.market.models import (
    MarketSentiment,
)

logger = get_logger(__name__)


def analyze_market_sentiment() -> MarketSentiment:
    """
    Analyze overall market sentiment.

    Returns
    -------
    MarketSentiment
    """

    logger.info(
        "Analyzing market sentiment..."
    )

    try:

        # ==================================================
        # PLACEHOLDER DATA
        # ==================================================

        fear_greed_index = 68

        news_score = 0.72

        foreign_flow = 0.63

        # ==================================================
        # SCORE
        # ==================================================

        score = 0

        if fear_greed_index >= 60:
            score += 1

        if news_score >= 0.60:
            score += 1

        if foreign_flow >= 0.60:
            score += 1

        normalized_score = round(
            score / 3 * 100,
            2,
        )

        # ==================================================
        # STATUS
        # ==================================================

        if score == 3:

            status = "GREED"

        elif score == 2:

            status = "NEUTRAL"

        else:

            status = "FEAR"

        summary = (
            f"{status} market sentiment "
            f"({normalized_score:.0f}/100)"
        )

        logger.info(
            "Market sentiment calculated."
        )

        return MarketSentiment(

            status=status,

            score=normalized_score,

            summary=summary,

        )

    except Exception as exc:

        logger.exception(
            "Market sentiment calculation failed."
        )

        raise MarketError(
            str(exc)
        ) from exc