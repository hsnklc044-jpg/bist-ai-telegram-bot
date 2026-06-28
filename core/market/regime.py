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

from core.market.models import (
    MarketBreadth,
    MarketRegime,
    MarketSentiment,
)

logger = get_logger(__name__)


def determine_market_regime(
    trend: str,
    breadth: MarketBreadth,
    sentiment: MarketSentiment,
) -> MarketRegime:
    """
    Determine the current market regime.

    Parameters
    ----------
    trend
        Current market trend.

    breadth
        Market breadth analysis.

    sentiment
        Market sentiment analysis.

    Returns
    -------
    MarketRegime
    """

    logger.info(
        "Determining market regime..."
    )

    try:

        score = 0

        # ------------------------------------------
        # Trend
        # ------------------------------------------

        if trend.upper() == "BULLISH":
            score += 40

        elif trend.upper() == "NEUTRAL":
            score += 20

        # ------------------------------------------
        # Breadth
        # ------------------------------------------

        score += breadth.score * 0.30

        # ------------------------------------------
        # Sentiment
        # ------------------------------------------

        score += sentiment.score * 0.30

        score = round(
            min(score, 100),
            2,
        )

        # ------------------------------------------
        # Regime
        # ------------------------------------------

        if score >= 70:

            status = "RISK_ON"

        elif score >= 45:

            status = "NEUTRAL"

        else:

            status = "RISK_OFF"

        summary = (
            f"{status} market "
            f"({score:.0f}/100)"
        )

        logger.info(
            "Market regime calculated."
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