"""
QuantBIST RC5
AI Recommendation Engine

Generates human readable AI investment report.
"""

from __future__ import annotations


from core.decision.models import Decision





# =====================================================
# OVERVIEW
# =====================================================


def _build_overview(
    decision: Decision,
) -> list[str]:

    return [

        "=== AI DECISION OVERVIEW ===",

        f"Decision ID    : {decision.decision_id}",

        f"Time           : {decision.timestamp:%Y-%m-%d %H:%M}",

        f"Recommendation : {decision.action}",

        f"AI Score       : {decision.ai_score}/100",

        f"Confidence     : {decision.confidence}%",

        f"Priority       : {decision.priority}",

        f"Engine         : {decision.engine_version}",

    ]





# =====================================================
# PORTFOLIO
# =====================================================


def _portfolio_section(
    decision: Decision,
) -> list[str]:

    lines = [

        "=== PORTFOLIO INTELLIGENCE ===",

        f"Grade          : {decision.portfolio_grade}",

        f"Health         : {decision.portfolio_health:.1f}/100",

        f"Risk Level     : {decision.risk_level}",

        f"Risk Score     : {decision.risk_score:.1f}",

    ]


    if decision.best_symbol:

        lines.append(

            f"Best Position  : {decision.best_symbol}"

        )


    if decision.worst_symbol:

        lines.append(

            f"Weak Position : {decision.worst_symbol}"

        )


    if decision.rebalance_required:

        lines.append(

            "Action         : Portfolio rebalance required."

        )

    else:

        lines.append(

            "Action         : Portfolio structure stable."

        )


    return lines





# =====================================================
# MARKET
# =====================================================


def _market_section(
    decision: Decision,
) -> list[str]:

    return [

        "=== MARKET INTELLIGENCE ===",

        f"Status         : {decision.market_status}",

        f"Trend          : {decision.market_trend}",

        f"Regime         : {decision.market_regime}",

    ]





# =====================================================
# SCORE BREAKDOWN
# =====================================================


def _score_section(
    decision: Decision,
) -> list[str]:

    lines = [

        "=== AI SCORE BREAKDOWN ==="

    ]


    labels = {

        "portfolio_health":
            "Portfolio Health",

        "committee_score":
            "Committee Score",

        "market_score":
            "Market Score",

        "risk_factor":
            "Risk Impact",

    }


    for key, value in decision.score_breakdown.items():


        label = labels.get(

            key,

            key,

        )


        lines.append(

            f"{label:<18}: {value:.2f}"

        )


    return lines





# =====================================================
# AI EXPLANATION
# =====================================================


def _explanation_section(
    decision: Decision,
) -> list[str]:


    if not decision.ai_explanation:

        return [

            "=== AI REASONING ===",

            "AI explanation unavailable.",

            "Decision generated from quantitative analysis.",

        ]


    return [

        "=== AI REASONING ===",

        *decision.ai_explanation,

    ]





# =====================================================
# COMMITTEE
# =====================================================


def _committee_section(
    decision: Decision,
) -> list[str]:

    return [

        "=== COMMITTEE ANALYSIS ===",

        f"Committee Action : {decision.committee_action}",

        f"Committee Score  : {decision.committee_score:.2f}",

        f"Consensus        : {decision.committee_consensus:.2f}%",


    ]





# =====================================================
# REASONS
# =====================================================


def _reason_section(
    decision: Decision,
) -> list[str]:

    return [

        "=== DECISION REASONS ===",

        *(

            decision.reasons

            if decision.reasons

            else [

                "No additional reasons."

            ]

        )

    ]





# =====================================================
# SUGGESTIONS
# =====================================================


def _suggestion_section(
    decision: Decision,
) -> list[str]:

    return [

        "=== AI SUGGESTIONS ===",

        *(

            decision.suggestions

            if decision.suggestions

            else [

                "No suggestions."

            ]

        )

    ]





# =====================================================
# WARNINGS
# =====================================================


def _warning_section(
    decision: Decision,
) -> list[str]:

    return [

        "=== RISK WARNINGS ===",

        *(

            decision.warnings

            if decision.warnings

            else [

                "No warnings."

            ]

        )

    ]





# =====================================================
# PUBLIC API
# =====================================================


def generate_recommendation(
    decision: Decision,
) -> str:
    """
    Generate RC5 AI executive recommendation.
    """


    sections: list[str] = []


    sections.extend(
        _build_overview(decision)
    )


    sections.append("")


    sections.extend(
        _portfolio_section(decision)
    )


    sections.append("")


    sections.extend(
        _market_section(decision)
    )


    sections.append("")


    sections.extend(
        _score_section(decision)
    )


    sections.append("")


    sections.extend(
        _committee_section(decision)
    )


    sections.append("")


    sections.extend(
        _explanation_section(decision)
    )


    sections.append("")


    sections.extend(
        _reason_section(decision)
    )


    if decision.suggestions:

        sections.append("")

        sections.extend(
            _suggestion_section(decision)
        )


    if decision.warnings:

        sections.append("")

        sections.extend(
            _warning_section(decision)
        )


    return "\n".join(sections)





__all__ = [

    "generate_recommendation",

]
