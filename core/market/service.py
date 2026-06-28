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

from core.market.analyzer import (
    analyze_market,
)

from core.market.models import (
    MarketStatus,
)

logger = get_logger(__name__)


def get_market_status() -> MarketStatus:
    """
    Public entry point for the Market Engine.

    Returns
    -------
    MarketStatus
    """

    logger.info(
        "Market Service started."
    )

    try:

        market = analyze_market()

        logger.info(
            "Market Service completed."
        )

        return market

    except MarketError:

        raise

    except Exception as exc:

        logger.exception(
            "Market Service failed."
        )

        raise MarketError(
            str(exc)
        ) from exc