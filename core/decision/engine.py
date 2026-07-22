"""
QuantBIST RC5
Decision Engine Compatibility Layer

Legacy support for old imports.
"""

from __future__ import annotations


from core.decision.models import Decision
from core.decision.service import get_decision
from core.infrastructure.exceptions import DecisionError
from core.infrastructure.logger import get_logger
from core.portfolio.models import PortfolioStats



logger = get_logger(__name__)




# =====================================================
# LEGACY PUBLIC API
# =====================================================


def generate_decision(
    stats: PortfolioStats,
) -> Decision:
    """
    Legacy wrapper.

    Old:

        generate_decision(stats)

    New:

        get_decision(stats)

    """

    logger.info(
        "Legacy Decision Engine call redirected to Decision Service."
    )


    try:

        return get_decision(
            stats
        )


    except DecisionError:

        raise


    except Exception as exc:


        logger.exception(
            "Decision Engine failed."
        )


        raise DecisionError(
            str(exc)
        ) from exc



# =====================================================
# EXPORTS
# =====================================================


__all__ = [

    "generate_decision",

]