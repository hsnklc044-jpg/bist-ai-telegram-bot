"""
QuantBIST RC5
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


from core.market.service import (
    get_market_status,
)


from core.portfolio.service import (
    get_portfolio_analysis,
)




logger = get_logger(__name__)





# =====================================================
# PUBLIC API
# =====================================================


def get_decision(
    portfolio_stats,
) -> Decision:
    """
    Build final QuantBIST AI decision.

    Flow:

        Portfolio Stats
              ↓
        Portfolio Intelligence
              ↓
        Market Intelligence
              ↓
        Investment Committee
              ↓
        Decision Builder
              ↓
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





        # -----------------------------------------
        # Portfolio
        # -----------------------------------------


        portfolio = get_portfolio_analysis(

            portfolio_stats,

        )





        # -----------------------------------------
        # Market
        # -----------------------------------------


        market = get_market_status()





        # -----------------------------------------
        # Committee
        # -----------------------------------------


        committee = get_committee_decision(

            portfolio,

            market,

        )





        # -----------------------------------------
        # Final Decision
        # -----------------------------------------


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
# SHORTCUTS
# =====================================================


def buy_signal(
    portfolio_stats,
) -> bool:

    return get_decision(

        portfolio_stats

    ).buy_signal





def sell_signal(
    portfolio_stats,
) -> bool:

    return get_decision(

        portfolio_stats

    ).sell_signal





def rebalance_signal(
    portfolio_stats,
) -> bool:

    return get_decision(

        portfolio_stats

    ).rebalance_signal





def high_confidence(
    portfolio_stats,
) -> bool:

    return get_decision(

        portfolio_stats

    ).high_confidence





def critical(
    portfolio_stats,
) -> bool:

    return get_decision(

        portfolio_stats

    ).critical





def accumulate_signal(
    portfolio_stats,
) -> bool:
    """
    Accumulate recommendation check.
    """

    return get_decision(

        portfolio_stats

    ).accumulate_signal





def strong_buy_signal(
    portfolio_stats,
) -> bool:
    """
    Strong buy recommendation check.
    """

    return get_decision(

        portfolio_stats

    ).strong_buy_signal





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