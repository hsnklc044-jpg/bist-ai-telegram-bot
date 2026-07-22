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

        Portfolio
            ↓
        Market
            ↓
        Committee
            ↓
        Decision Builder
            ↓
        Decision

    """


    logger.info(

        "Generating QuantBIST decision."

    )



    try:


        portfolio = get_portfolio_analysis(

            portfolio_stats,

        )



        market = get_market_status()



        committee = get_committee_decision(

            portfolio,

            market,

        )



        decision = build_decision(

            committee=committee,

            portfolio=portfolio,

            market=market,

        )




        logger.info(

            "Decision completed | "
            "Action=%s | Score=%d | Confidence=%d",

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