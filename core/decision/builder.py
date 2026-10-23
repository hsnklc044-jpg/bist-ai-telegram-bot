"""
QuantBIST RC7
Decision Builder

Build final AI investment decision.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from core.ai.scoring import (
    calculate_score,
)
from core.config.thresholds import action_for_score
from core.decision.models import (
    Decision,
    PriorityLevel,
)

# =====================================================
# HELPERS
# =====================================================


def _id() -> str:

    return (

        f"DEC-{datetime.now():%Y%m%d}-"

        f"{uuid4().hex[:8].upper()}"

    )





def _enum_value(value):

    if hasattr(value, "value"):

        return value.value

    return str(value)







# =====================================================
# ACTION
# =====================================================


def _action(
    score: int,
) -> str:

    return action_for_score(score)



# =====================================================
# RISK
# =====================================================


def _risk_score(
    portfolio,
):

    mapping = {


        "LOW":20,


        "MEDIUM":50,


        "HIGH":75,


        "VERY_HIGH":85,


        "CRITICAL":95,

    }


    level = _enum_value(

        portfolio.risk.level

    ).upper()



    return mapping.get(

        level,

        50,

    )







def _confidence(
    committee,
):

    return max(

        0,

        min(

            99,

            int(

                committee.confidence

            ),

        )

    )






# =====================================================
# TEXT
# =====================================================


def _recommendation(
    action,
    score,
    confidence,
):

    return (

        f"{action} recommendation | "

        f"AI Score={score}/100 | "

        f"Confidence={confidence}%"

    )






def _reasons(
    score,
    portfolio,
    market,
    committee,
):

    return [

        f"AI Score: {score}/100",

        f"Market Trend: {_enum_value(market.trend)}",

        f"Market Regime: {_enum_value(market.regime.status)}",

        f"Portfolio Grade: {portfolio.health.grade}",

        f"Committee Decision: {_enum_value(committee.action)}",

    ]







def _warnings(
    portfolio,
    market,
):

    result = []


    if portfolio.rebalance.needs_rebalance:

        result.append(

            "Portfolio rebalance required."

        )


    if market.risk_off:

        result.append(

            "Market risk-off condition."

        )


    return result







# =====================================================
# PUBLIC API
# =====================================================


def build_decision(
    committee,
    portfolio,
    market,
) -> Decision:
    """
    Build final RC7 decision.
    """


    score = calculate_score(

        portfolio,

        market,

    )



    action = _action(

        score,

    )



    confidence = _confidence(

        committee,

    )



    risk_score = _risk_score(

        portfolio,

    )



    decision = Decision(



        decision_id=_id(),



        action=action,



        score=score,



        ai_score=score,



        confidence=confidence,



        priority=(

            PriorityLevel.HIGH.value

            if confidence < 60

            else PriorityLevel.NORMAL.value

        ),



        summary=(

            f"{action} | "

            f"AI {score}/100 | "

            f"Confidence {confidence}%"

        ),



        recommendation=_recommendation(

            action,

            score,

            confidence,

        ),



        risk_level=_enum_value(

            portfolio.risk.level

        ),



        risk_score=risk_score,





        market_status=_enum_value(

            market.status

        ),



        market_trend=_enum_value(

            market.trend

        ),



        market_regime=_enum_value(

            market.regime.status

        ),




        portfolio_health=portfolio.health.score,



        portfolio_grade=portfolio.health.grade,



        rebalance_required=

            portfolio.rebalance.needs_rebalance,




        committee_action=_enum_value(

            committee.action

        ),



        committee_score=committee.score,



        committee_consensus=committee.consensus,




        reasons=_reasons(

            score,

            portfolio,

            market,

            committee,

        ),



        warnings=_warnings(

            portfolio,

            market,

        ),



        suggestions=[

            "Monitor market conditions.",

        ],

    )



    return decision







__all__ = [

    "build_decision",

]