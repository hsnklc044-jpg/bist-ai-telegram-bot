"""
QuantBIST Framework
Market Analyzer
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

from core.market.models import (
    MarketStatus,
)

from core.market.regime import (
    determine_market_regime,
)

from core.market.scanner import (
    scan_market,
)

from core.market.sentiment import (
    analyze_market_sentiment,
)

logger = get_logger(__name__)


def analyze_market() -> MarketStatus:
    """
    Execute the complete Market Engine.

    Returns
    -------
    MarketStatus
    """

    logger.info(
        "Market analysis started."
    )

    try:

        # ------------------------------------------
        # Raw Market Scan
        # ------------------------------------------

        raw_market = scan_market()

        # ------------------------------------------
        # Breadth
        # ------------------------------------------

        breadth = calculate_market_breadth()

        # ------------------------------------------
        # Sentiment
        # ------------------------------------------

        sentiment = analyze_market_sentiment()

        # ------------------------------------------
        # Regime
        # ------------------------------------------

        regime = determine_market_regime(

            trend=raw_market.trend,

            breadth=breadth,

            sentiment=sentiment,

        )

        logger.info(
            "Market analysis completed."
        )

        return MarketStatus(

            status=raw_market.status,

            index=raw_market.index,

            change=raw_market.change,

            trend=raw_market.trend,

            breadth=breadth,

            sentiment=sentiment,

            volatility=raw_market.volatility,

            regime=regime,

        )

    except MarketError:

        raise

    except Exception as exc:

        logger.exception(
            "Market analysis failed."
        )

        raise MarketError(
            str(exc)
        ) from exc
