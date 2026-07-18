"""
QuantBIST Framework
Decision Service
"""

from __future__ import annotations

from core.decision.engine import (
    generate_decision,
)

from core.decision.models import (
    Decision,
)

from core.infrastructure.exceptions import (
    DecisionError,
)

from core.infrastructure.logger import (
    get_logger,
)

from core.portfolio.models import (
    PortfolioStats,
)

logger = get_logger(__name__)


# =====================================================
# PUBLIC API
# =====================================================

def get_decision(
    stats: PortfolioStats,
) -> Decision:
    """
    Execute the complete Decision Engine.

    This service is the only public entry point
    for the Decision package.

    Parameters
    ----------
    stats
        Portfolio dashboard statistics.

    Returns
    -------
    Decision
    """

    logger.info(
        "Decision Service started."
    )

    try:

        decision = generate_decision(
            stats,
        )

        logger.info(

            "Decision generated: %s (%d%%)",

            decision.action,

            decision.confidence,

        )

        return decision

    except DecisionError:

        raise

    except Exception as exc:

        logger.exception(
            "Decision Service failed."
        )

        raise DecisionError(
            str(exc)
        ) from exc


# =====================================================
# SHORTCUTS
# =====================================================

def buy_signal(
    decision: Decision,
) -> bool:
    """
    Returns True if decision is BUY.
    """

    return decision.buy_signal


def sell_signal(
    decision: Decision,
) -> bool:
    """
    Returns True if decision is SELL.
    """

    return decision.sell_signal


def rebalance_signal(
    decision: Decision,
) -> bool:
    """
    Returns True if rebalancing is required.
    """

    return decision.rebalance_signal


def high_confidence(
    decision: Decision,
) -> bool:
    """
    Returns True if confidence is high.
    """

    return decision.high_confidence


def critical(
    decision: Decision,
) -> bool:
    """
    Returns True if priority is critical.
    """

    return decision.critical


# =====================================================
# EXPORTS
# =====================================================

__all__ = [

    "get_decision",

    "buy_signal",

    "sell_signal",

    "rebalance_signal",

    "high_confidence",

    "critical",

]