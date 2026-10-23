"""
QuantBIST RC7
Summary Report
"""

from __future__ import annotations

from core.models.dashboard import (
    DashboardModel,
)


def generate_summary_report(
    dashboard: DashboardModel,
) -> str:
    """
    Generate complete dashboard summary report.

    RC7:
    - No duplicate calculations
    - Uses DashboardModel
    - Single intelligence source
    """



    decision = dashboard.decision







    if decision is None:

        return "Decision data unavailable."





    return f"""
📊 QUANTBIST SUMMARY

════════════════════

🤖 AI DECISION

Action :
{decision.action}

AI Score :
{decision.ai_score}

Confidence :
{decision.confidence}%


════════════════════

💼 PORTFOLIO

Portfolio Value :
{dashboard.stats.get("portfolio", 0):,.2f} TL

Positions :
{dashboard.stats.get("positions", 0)}

Cash :
{dashboard.stats.get("cash", 0):,.2f} TL

Top Stock :
{dashboard.stats.get("top_stock", "-")}


════════════════════

📈 MARKET

Trend :
{decision.market_trend}

Regime :
{decision.market_regime}


════════════════════

⚠️ RISK

Level :
{decision.risk_level}

Risk Score :
{decision.risk_score}


════════════════════

📌 SUMMARY

{decision.summary}


════════════════════
"""





# =====================================================
# EXPORTS
# =====================================================


__all__ = [

    "generate_summary_report",

]
