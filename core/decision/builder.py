"""
QuantBIST RC5
Decision Builder

Builds final AI investment decision.
"""

from __future__ import annotations


from datetime import datetime
from uuid import uuid4


from core.ai.scoring import calculate_score

from core.committee.models import (
    CommitteeResult,
    Vote,
)

from core.decision.models import (
    Decision,
    DecisionAction,
)

from core.market.models import (
    MarketStatus,
)

from core.portfolio.models import (
    PortfolioAnalysis,
)





# =====================================================
# HELPERS
# =====================================================


def _generate_decision_id() -> str:

    return (

        f"DEC-{datetime.now():%Y%m%d}-"

        f"{uuid4().hex[:8].upper()}"

    )





def _enum_value(
    value,
) -> str:

    if hasattr(
        value,
        "value",
    ):

        return str(
            value.value
        ).upper()


    return str(
        value
    ).upper()






def _risk_score(
    portfolio: PortfolioAnalysis,
) -> float:


    mapping = {

        "LOW":20.0,

        "MEDIUM":50.0,

        "HIGH":75.0,

        "VERY_HIGH":85.0,

        "CRITICAL":95.0,

    }


    return mapping.get(

        _enum_value(

            portfolio.risk.level

        ),

        50.0,

    )






def _confidence(
    value:int,
) -> int:


    return max(

        0,

        min(

            99,

            int(value),

        )

    )






# =====================================================
# ACTION ENGINE
# =====================================================


def _final_action(
    ai_score:int,
    committee:CommitteeResult,
    portfolio:PortfolioAnalysis,
) -> str:


    risk = _enum_value(

        portfolio.risk.level

    )


    action = committee.action





    if risk in (

        "CRITICAL",

        "VERY_HIGH",

    ):

        return DecisionAction.REDUCE.value






    if (

        ai_score >= 90

        and

        action == Vote.STRONG_BUY

        and

        committee.confidence >= 80

    ):

        return DecisionAction.STRONG_BUY.value






    if (

        ai_score >= 75

        and

        action in (

            Vote.BUY,

            Vote.STRONG_BUY,

        )

    ):

        return DecisionAction.BUY.value






    if (

        ai_score >=70

        and

        action == Vote.HOLD

    ):

        return DecisionAction.WATCH.value






    if ai_score <=35:

        return DecisionAction.SELL.value






    if action in (

        Vote.REDUCE,

        Vote.SELL,

    ):

        return _enum_value(action)





    return _enum_value(action)







# =====================================================
# EXPLANATION
# =====================================================


def _ai_explanation(
    portfolio,
    market,
    committee,
    score,
):

    result = []


    result.append(

        f"AI Score: {score}/100"

    )


    result.append(

        f"Market regime: {market.regime.status.value}"

    )


    result.append(

        f"Market trend: {market.trend.value}"

    )


    result.append(

        f"Portfolio health: {portfolio.health.score}/100"

    )


    result.append(

        f"Committee decision: {_enum_value(committee.action)}"

    )



    if market.risk_off:

        result.append(

            "Risk-Off environment detected."

        )



    if portfolio.rebalance.needs_rebalance:

        result.append(

            "Portfolio rebalance required."

        )


    return result







def _score_breakdown(
    portfolio,
    market,
    committee,
):

    return {

        "portfolio_health":

            float(

                portfolio.health.score

            ),


        "market_score":

            float(

                market.market_score

            ),


        "committee_score":

            float(

                committee.score

            ),


        "risk_factor":

            -_risk_score(

                portfolio

            ),

    }







def _decision_context(
    portfolio,
    market,
):

    return {

        "market_status":

            market.status,


        "trend":

            market.trend.value,


        "regime":

            market.regime.status.value,


        "portfolio_grade":

            portfolio.health.grade,


        "risk":

            _enum_value(

                portfolio.risk.level

            ),

    }







def _warnings(
    portfolio,
    market,
):

    warnings = []


    if portfolio.rebalance.needs_rebalance:

        warnings.append(

            "Portfolio rebalance required."

        )


    if portfolio.optimization.concentration_risk:

        warnings.append(

            "Concentration risk detected."

        )


    if market.risk_off:

        warnings.append(

            "Market risk-off condition."

        )


    if market.volatility.value == "HIGH":

        warnings.append(

            "High volatility environment."

        )


    return warnings







def _suggestions(
    portfolio,
    market,
):

    suggestions = []


    if market.risk_on:

        suggestions.append(

            "Selective equity exposure can be maintained."

        )


    if portfolio.rebalance.needs_rebalance:

        suggestions.append(

            "Review target portfolio weights."

        )


    if not suggestions:

        suggestions.append(

            "Monitor market conditions."

        )


    return suggestions







# =====================================================
# PUBLIC API
# =====================================================


def build_decision(
    committee:CommitteeResult,
    portfolio:PortfolioAnalysis,
    market:MarketStatus,
) -> Decision:


    ai_score = calculate_score(

        portfolio,

        market,

    )



    action = _final_action(

        ai_score,

        committee,

        portfolio,

    )



    confidence = _confidence(

        committee.confidence

    )



    return Decision(

        decision_id=_generate_decision_id(),

        timestamp=datetime.now(),

        engine_version="RC5",


        action=action,


        score=ai_score,


        confidence=confidence,


        priority=_enum_value(

            committee.priority

        ),


        summary=(

            f"{action} | "

            f"AI {ai_score}/100 | "

            f"Confidence {confidence}%"

        ),



        ai_score=ai_score,



        ai_explanation=_ai_explanation(

            portfolio,

            market,

            committee,

            ai_score,

        ),



        score_breakdown=_score_breakdown(

            portfolio,

            market,

            committee,

        ),



        decision_context=_decision_context(

            portfolio,

            market,

        ),



        committee_action=_enum_value(

            committee.action

        ),



        committee_score=committee.score,


        committee_consensus=committee.consensus,



        portfolio_health=portfolio.health.score,


        portfolio_grade=portfolio.health.grade,


        best_symbol=portfolio.optimization.largest_position,


        worst_symbol=portfolio.optimization.smallest_position,



        rebalance_required=portfolio.rebalance.needs_rebalance,



        risk_level=_enum_value(

            portfolio.risk.level

        ),



        risk_score=_risk_score(

            portfolio

        ),



        market_status=market.status,


        market_trend=market.trend.value,


        market_regime=market.regime.status.value,



        reasons=_ai_explanation(

            portfolio,

            market,

            committee,

            ai_score,

        ),



        suggestions=_suggestions(

            portfolio,

            market,

        ),



        warnings=_warnings(

            portfolio,

            market,

        ),

    )






__all__=[

    "build_decision",

]