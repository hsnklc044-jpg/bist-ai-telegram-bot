"""
QuantBIST RC6
Decision Report

AI decision explanation layer.
"""

from __future__ import annotations


from core.decision.models import (
    Decision,
)





# =====================================================
# PUBLIC API
# =====================================================


def generate_decision_report(
    decision: Decision,
) -> str:
    """
    Generate AI decision report.

    Source:

        Decision Intelligence

    """



    if decision is None:

        raise ValueError(
            "Decision cannot be empty."
        )





    reasons = "\n".join(

        f"- {item}"

        for item in decision.reasons

    )



    warnings = "\n".join(

        f"- {item}"

        for item in decision.warnings

    )



    suggestions = "\n".join(

        f"- {item}"

        for item in decision.suggestions

    )





    return f"""
🤖 QUANTBIST RC6 AI DECISION REPORT

════════════════════

📌 FINAL ACTION


{decision.action}



🎯 AI SCORE


{decision.ai_score}/100



📊 DECISION SCORE


{decision.score}/100



🔒 CONFIDENCE


{decision.confidence}%



⭐ PRIORITY


{decision.priority}



════════════════════

🏛️ INVESTMENT COMMITTEE


Action:

{decision.committee_action}


Score:

{decision.committee_score}


Consensus:

{decision.committee_consensus}



════════════════════

📈 TECHNICAL INTELLIGENCE


Technical Score:

{decision.technical_score}


Trend:

{decision.technical_trend}


RSI:

{decision.rsi}


MACD:

{decision.macd_signal}



════════════════════

🌍 MARKET


Trend:

{decision.market_trend}


Regime:

{decision.market_regime}



════════════════════

💼 PORTFOLIO


Health:

{decision.portfolio_health}


Grade:

{decision.portfolio_grade}


Rebalance:

{decision.rebalance_required}



════════════════════

⚠️ RISK


Level:

{decision.risk_level}


Score:

{decision.risk_score}



════════════════════

🧠 AI EXPLANATION


{decision.explanation_text}



════════════════════

✅ REASONS


{reasons if reasons else "No reasons available."}



════════════════════

⚠️ WARNINGS


{warnings if warnings else "No warnings available."}



════════════════════

💡 SUGGESTIONS


{suggestions if suggestions else "No suggestions available."}



════════════════════
"""





# =====================================================
# SHORTCUT
# =====================================================


def decision_summary(
    decision: Decision,
) -> str:
    """
    Short decision summary.
    """

    return (

        f"{decision.action} | "

        f"AI={decision.ai_score} | "

        f"Confidence={decision.confidence}%"

    )





# =====================================================
# EXPORTS
# =====================================================


__all__ = [

    "generate_decision_report",

    "decision_summary",

]