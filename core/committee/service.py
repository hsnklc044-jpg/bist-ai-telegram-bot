"""
QuantBIST Framework
Investment Committee Service
"""

from __future__ import annotations

from core.committee.engine import (
    run_committee,
)

from core.committee.models import (
    CommitteeResult,
)

from core.infrastructure.exceptions import (
    DecisionError,
)

from core.infrastructure.logger import (
    get_logger,
)

from core.market.models import (
    MarketStatus,
)

from core.portfolio.models import (
    PortfolioAnalysis,
)

logger = get_logger(__name__)


# =====================================================
# PUBLIC API
# =====================================================

def get_committee_decision(
    portfolio: PortfolioAnalysis,
    market: MarketStatus,
) -> CommitteeResult:
    """
    Execute the complete Investment Committee.

    This is the only public entry point of the
    Committee package.
    """

    logger.info(
        "Committee Service started."
    )

    try:

        result = run_committee(

            portfolio,

            market,

        )

        logger.info(

            "Committee decision: %s (%d%%)",

            result.action.value,

            result.confidence,

        )

        return result

    except DecisionError:

        raise

    except Exception as exc:

        logger.exception(
            "Committee Service failed."
        )

        raise DecisionError(
            str(exc)
        ) from exc


# =====================================================
# SHORTCUTS
# =====================================================

def buy_signal(
    committee: CommitteeResult,
) -> bool:
    """
    Buy recommendation?
    """

    return committee.buy_signal


def sell_signal(
    committee: CommitteeResult,
) -> bool:
    """
    Sell recommendation?
    """

    return committee.sell_signal


def high_confidence(
    committee: CommitteeResult,
) -> bool:
    """
    High confidence decision?
    """

    return committee.high_confidence


def unanimous(
    committee: CommitteeResult,
) -> bool:
    """
    Committee unanimous?
    """

    return committee.unanimous


# =====================================================
# EXPORTS
# =====================================================

__all__ = [

    "get_committee_decision",

    "buy_signal",

    "sell_signal",

    "high_confidence",

    "unanimous",

]