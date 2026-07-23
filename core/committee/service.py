"""
QuantBIST RC5
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
# HELPERS
# =====================================================


def _action_value(
    action,
) -> str:
    """
    Convert enum action safely.
    """

    if hasattr(

        action,

        "value",

    ):

        return str(
            action.value
        )


    return str(action)







# =====================================================
# PUBLIC API
# =====================================================


def get_committee_decision(
    portfolio: PortfolioAnalysis,
    market: MarketStatus,
) -> CommitteeResult:
    """
    Execute Investment Committee.

    Flow:

        Portfolio
            ↓
        Market
            ↓
        Committee Engine
            ↓
        Committee Result

    """



    logger.info(

        "Investment Committee analysis started."

    )



    try:


        result = run_committee(

            portfolio,

            market,

        )



        if result is None:


            raise DecisionError(

                "Committee returned empty result."

            )




        logger.info(

            "Committee completed | "
            "Action=%s | Score=%.2f | Confidence=%d | Consensus=%.2f",

            _action_value(

                result.action,

            ),

            result.score,

            result.confidence,

            result.consensus,

        )




        return result





    except DecisionError:

        raise





    except Exception as exc:


        logger.exception(

            "Investment Committee service failed."

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
    Committee buy signal.
    """

    return committee.buy_signal






def sell_signal(
    committee: CommitteeResult,
) -> bool:
    """
    Committee sell signal.
    """

    return committee.sell_signal






def high_confidence(
    committee: CommitteeResult,
) -> bool:
    """
    High confidence committee decision.
    """

    return committee.high_confidence






def unanimous(
    committee: CommitteeResult,
) -> bool:
    """
    All members agree.
    """

    return committee.unanimous






def consensus(
    committee: CommitteeResult,
) -> int:
    """
    Return consensus percentage.
    """

    return committee.consensus_percent






def is_strong_buy(
    committee: CommitteeResult,
) -> bool:
    """
    Strong buy committee decision.
    """

    return (

        _action_value(

            committee.action,

        )

        ==

        "STRONG BUY"

    )







def risk_warning(
    committee: CommitteeResult,
) -> bool:
    """
    Committee risk warning.
    """

    return committee.sell_signal







def decision_summary(
    committee: CommitteeResult,
) -> dict:
    """
    Dashboard friendly committee summary.
    """

    return {

        "action":

            _action_value(

                committee.action,

            ),


        "score":

            committee.score,


        "confidence":

            committee.confidence,


        "consensus":

            committee.consensus_percent,


        "priority":

            committee.priority,


    }







# =====================================================
# EXPORTS
# =====================================================


__all__ = [

    "get_committee_decision",

    "buy_signal",

    "sell_signal",

    "high_confidence",

    "unanimous",

    "consensus",

    "is_strong_buy",

    "risk_warning",

    "decision_summary",

]
