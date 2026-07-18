"""
QuantBIST Framework
Decision Engine
"""

from __future__ import annotations

from core.committee.service import (
    get_committee_decision,
)

from core.decision.builder import (
    build_decision,
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

from core.market.service import (
    get_market_status,
)

from core.portfolio.models import (
    PortfolioStats,
)

from core.portfolio.service import (
    get_portfolio_analysis,
)

logger = get_logger(__name__)


# =====================================================
# PUBLIC API
# =====================================================

def generate_decision(
    stats: PortfolioStats,
) -> Decision:
    """
    Execute the complete Decision Engine.

    Workflow
    --------
    Portfolio
        ↓
    Market
        ↓
    Investment Committee
        ↓
    Decision Builder
        ↓
    Decision
    """

    logger.info(
        "Decision Engine started."
    )

    try:

        # -------------------------------------------------
        # Portfolio
        # -------------------------------------------------

        portfolio = get_portfolio_analysis(
            stats,
        )

        # -------------------------------------------------
        # Market
        # -------------------------------------------------

        market = get_market_status()

        # -------------------------------------------------
        # Investment Committee
        # -------------------------------------------------

        committee = get_committee_decision(

            portfolio,

            market,

        )

        # -------------------------------------------------
        # Decision Builder
        # -------------------------------------------------

        decision = build_decision(

            committee=committee,

            portfolio=portfolio,

            market=market,

        )

        logger.info(

            "Decision completed: %s (%d%%)",

            decision.action,

            decision.confidence,

        )

        return decision

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