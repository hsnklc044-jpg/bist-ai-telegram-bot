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

from core.market.models import (
    MarketBreadth,
)

logger = get_logger(__name__)


def calculate_market_breadth() -> MarketBreadth:
    """
    Calculate overall market breadth.

    Returns
    -------
    MarketBreadth
    """

    logger.info(
        "Calculating market breadth..."
    )

    try:

        # ==================================================
        # PLACEHOLDER DATA
        # ==================================================

        advance_decline_ratio = 1.35

        sector_strength = 0.72

        volume_participation = 0.81

        # ==================================================
        # SCORE
        # ==================================================

        score = 0

        if advance_decline_ratio > 1:
            score += 1

        if sector_strength >= 0.60:
            score += 1

        if volume_participation >= 0.70:
            score += 1

        normalized_score = round(
            score / 3 * 100,
            2,
        )

        # ==================================================
        # STATUS
        # ==================================================

        if score == 3:

            status = "POSITIVE"

        elif score == 2:

            status = "NEUTRAL"

        else:

            status = "NEGATIVE"

        summary = (
            f"{status} market breadth "
            f"({normalized_score:.0f}/100)"
        )

        logger.info(
            "Market breadth calculated."
        )

        return MarketBreadth(

            status=status,

            score=normalized_score,

            summary=summary,

        )

    except Exception as exc:

        logger.exception(
            "Market breadth calculation failed."
        )

        raise MarketError(
            str(exc)
        ) from exc