"""
QuantBIST RC7
Decision Service

Single public entry point
for Decision Engine.
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





logger = get_logger(__name__)





# =====================================================
# PUBLIC API
# =====================================================


def get_decision(
    portfolio_stats,
    portfolio,
    market,
) -> Decision:
    """
    Build final QuantBIST AI decision.

    RC7 Flow:

        Portfolio Stats
              |
        Portfolio Intelligence
              |
        Market Intelligence
              |
        Investment Committee
              |
        Decision Builder
              |
        Final Decision

    """



    logger.info(

        "Generating QuantBIST decision."

    )



    try:


        if portfolio_stats is None:

            raise DecisionError(
                "Portfolio statistics cannot be empty."
            )


        if portfolio is None:

            raise DecisionError(
                "Portfolio analysis cannot be empty."
            )


        if market is None:

            raise DecisionError(
                "Market status cannot be empty."
            )





        committee = get_committee_decision(

            portfolio,

            market,

        )





        decision = build_decision(

            committee=committee,

            portfolio=portfolio,

            market=market,

        )





        if decision is None:

            raise DecisionError(
                "Decision builder returned empty result."
            )





        logger.info(

            "Decision completed | "
            "Action=%s | AI=%d | Confidence=%d",

            decision.action,

            decision.ai_score,

            decision.confidence,

        )



        return decision





    except DecisionError:

        raise



    except Exception as exc:


        logger.exception(

            "Decision generation failed."

        )


        raise DecisionError(

            str(exc)

        ) from exc







# =====================================================
# SIGNAL HELPERS
# =====================================================


def buy_signal(
    decision: Decision,
) -> bool:

    return decision.buy_signal





def sell_signal(
    decision: Decision,
) -> bool:

    return decision.sell_signal





def rebalance_signal(
    decision: Decision,
) -> bool:

    return decision.rebalance_signal





def high_confidence(
    decision: Decision,
) -> bool:

    return decision.high_confidence





def critical(
    decision: Decision,
) -> bool:

    return decision.critical





def accumulate_signal(
    decision: Decision,
) -> bool:

    return decision.accumulate_signal





def strong_buy_signal(
    decision: Decision,
) -> bool:

    return decision.strong_buy_signal







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

    "accumulate_signal",

    "strong_buy_signal",

]
