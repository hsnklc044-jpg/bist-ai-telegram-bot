"""
QuantBIST Framework
Market Scanner
"""

from __future__ import annotations

from core.infrastructure.exceptions import (
    MarketScanError,
)

from core.infrastructure.logger import (
    get_logger,
)

from core.market.models import (
    MarketStatus,
)

logger = get_logger(__name__)


def scan_market() -> MarketStatus:
    """
    Scan the current market.

    Returns
    -------
    MarketStatus
    """

    logger.info(
        "Scanning market..."
    )

    try:

        #
        # TODO
        #
        # Buraya daha sonra
        #
        # Yahoo Finance
        # Finnhub
        # TradingView
        # Matriks
        # BIST API
        #
        # bağlanacak.
        #

        market = MarketStatus(

            status="OPEN",

            index="BIST100",

            change=1.42,

            trend="BULLISH",

            breadth="UNKNOWN",

            sentiment="UNKNOWN",

            volatility="LOW",

            regime="UNKNOWN",

        )

        logger.info(
            "Market scan completed."
        )

        return market

    except Exception as exc:

        logger.exception(
            "Market scan failed."
        )

        raise MarketScanError(
            str(exc)
        ) from exc
