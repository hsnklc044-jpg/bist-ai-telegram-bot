"""
QuantBIST RC7
Investment Committee Service

Public gateway for Investment Committee Engine.

Flow:

Portfolio
    |
Market
    |
Committee Engine
    |
Committee Result
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
    Generate investment committee decision.

    RC7 Pipeline:

        Portfolio Intelligence
                |
        Market Intelligence
                |
        Committee Engine
                |
        Committee Result

    """


    logger.info(

        "Investment Committee started."

    )



    try:



        if portfolio is None:

            raise DecisionError(

                "Portfolio missing."

            )



        if market is None:

            raise DecisionError(

                "Market data missing."

            )





        result = run_committee(

            portfolio,

            market,

        )





        if result is None:

            raise DecisionError(

                "Committee result empty."

            )





        logger.info(

            "Committee completed | "
            "Action=%s Score=%s Confidence=%s Consensus=%s",

            _action_value(

                result.action

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

            "Committee service failed."

        )


        raise DecisionError(

            str(exc)

        ) from exc







# =====================================================
# SIGNAL HELPERS
# =====================================================


def buy_signal(
    committee: CommitteeResult,
) -> bool:


    return committee.buy_signal







def sell_signal(
    committee: CommitteeResult,
) -> bool:


    return committee.sell_signal







def high_confidence(
    committee: CommitteeResult,
) -> bool:


    return committee.high_confidence







def unanimous(
    committee: CommitteeResult,
) -> bool:


    return committee.unanimous







def consensus(
    committee: CommitteeResult,
) -> float:
    """
    Committee agreement percentage.
    """


    return float(

        getattr(

            committee,

            "consensus",

            0,

        )

    )







def is_strong_buy(
    committee: CommitteeResult,
) -> bool:


    return (

        _action_value(

            committee.action

        )

        ==

        "STRONG BUY"

    )







def risk_warning(
    committee: CommitteeResult,
) -> bool:


    return committee.sell_signal







# =====================================================
# DASHBOARD OUTPUT
# =====================================================


def decision_summary(
    committee: CommitteeResult,
) -> dict:
    """
    Dashboard friendly committee card.
    """


    return {


        "action":

            _action_value(

                committee.action

            ),



        "score":

            committee.score,



        "confidence":

            committee.confidence,



        "consensus":

            consensus(

                committee

            ),



        "priority":

            committee.priority,



        "members":

            len(

                committee.votes

            )

            if hasattr(

                committee,

                "votes",

            )

            else 0,


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