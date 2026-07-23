"""
QuantBIST RC7
Portfolio Report

Portfolio intelligence reporting layer.
"""

from __future__ import annotations


from core.models.dashboard import (
    DashboardModel,
)





# =====================================================
# PUBLIC API
# =====================================================


def generate_portfolio_report(
    dashboard: DashboardModel,
) -> str:
    """
    Generate portfolio intelligence report.

    Source:

        DashboardModel
            |
            v
        PortfolioAnalysis

    """



    if dashboard is None:

        raise ValueError(
            "Dashboard cannot be empty."
        )





    portfolio = dashboard.portfolio



    if portfolio is None:

        return "Portfolio data unavailable."





    health = portfolio.health

    risk = portfolio.risk

    optimization = portfolio.optimization

    rebalance = portfolio.rebalance





    return f"""
💼 QUANTBIST RC7 PORTFOLIO REPORT

════════════════════

📊 PORTFOLIO SUMMARY


Portfolio Value:

{portfolio.stats.portfolio:,.2f} TL


Positions:

{portfolio.stats.positions}


Cash:

{portfolio.stats.cash:,.2f} TL


Top Stock:

{portfolio.stats.top_stock}



════════════════════

❤️ PORTFOLIO HEALTH


Health Score:

{health.score}


Grade:

{health.grade}



════════════════════

⚠️ RISK


Risk Level:

{risk.level}


Risk Score:

{risk.score}



Volatility:

{risk.volatility}


Max Drawdown:

{risk.max_drawdown}



════════════════════

🔄 REBALANCE


Required:

{rebalance.needs_rebalance}


Summary:

{rebalance.summary}



════════════════════

🏆 POSITION ANALYSIS


Best Symbol:

{optimization.best_symbol}


Worst Symbol:

{optimization.worst_symbol}



Largest Position:

{optimization.largest_position}


Largest Weight:

{optimization.largest_weight}



════════════════════

💡 SUGGESTIONS


{chr(10).join(
    "- " + item
    for item in optimization.suggestions
)
if optimization.suggestions
else "No suggestions available."
}



════════════════════
"""





# =====================================================
# SHORTCUT
# =====================================================


def portfolio_health(
    dashboard: DashboardModel,
) -> str:
    """
    Generate short health summary.
    """



    if dashboard.portfolio is None:

        return "Portfolio unavailable."



    health = dashboard.portfolio.health



    return (

        f"Health: {health.grade}"

        f" | Score: {health.score}"

    )





# =====================================================
# EXPORTS
# =====================================================


__all__ = [

    "generate_portfolio_report",

    "portfolio_health",

]
