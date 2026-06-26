"""
QuantBIST RC4
Summary Report
"""

from __future__ import annotations

from core.portfolio.dashboard_data import get_dashboard_stats


def generate_summary_report() -> str:
    """
    Generate portfolio summary report.
    """

    stats = get_dashboard_stats()

    return f"""
📊 QUANTBIST RC4 SUMMARY

════════════════════

💰 Portfolio Value :
{stats.portfolio:,.2f} TL

📂 Positions :
{stats.positions}

💵 Cash :
{stats.cash:,.2f} TL

🏆 Top Stock :
{stats.top_stock}

════════════════════

⚡ Sharpe :
{stats.sharpe}

🎯 Win Rate :
{stats.win_rate}%

🏅 Profit Factor :
{stats.profit_factor}

📉 Max Drawdown :
{stats.max_drawdown}%

════════════════════
"""