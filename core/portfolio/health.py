"""
QuantBIST RC4
Portfolio Health Engine
"""

from __future__ import annotations

from core.portfolio.models import PortfolioStats


def calculate_portfolio_health(
    stats: PortfolioStats,
) -> dict:
    """
    Portföy sağlığını hesaplar.

    Returns
    -------
    dict
        {
            "score": int,
            "grade": str,
            "risk": str,
            "cash_ratio": float,
            "diversification": str,
        }
    """

    # ----------------------------------
    # Cash Ratio
    # ----------------------------------

    if stats.portfolio > 0:

        cash_ratio = round(
            stats.cash / stats.portfolio * 100,
            2,
        )

    else:

        cash_ratio = 0.0

    # ----------------------------------
    # Health Score
    # ----------------------------------

    score = 100.0

    # Max Drawdown
    score -= stats.max_drawdown

    # Sharpe Ratio
    score += stats.sharpe * 2

    # Win Rate
    score += stats.win_rate / 10

    # Profit Factor
    score += stats.profit_factor * 5

    score = max(
        0.0,
        min(
            100.0,
            score,
        ),
    )

    score = round(score)

    # ----------------------------------
    # Grade
    # ----------------------------------

    if score >= 90:

        grade = "A"

    elif score >= 80:

        grade = "B"

    elif score >= 70:

        grade = "C"

    elif score >= 60:

        grade = "D"

    else:

        grade = "F"

    # ----------------------------------
    # Risk
    # ----------------------------------

    if cash_ratio >= 20:

        risk = "LOW"

    elif cash_ratio >= 10:

        risk = "MEDIUM"

    else:

        risk = "HIGH"

    # ----------------------------------
    # Diversification
    # ----------------------------------

    if stats.positions >= 10:

        diversification = "EXCELLENT"

    elif stats.positions >= 6:

        diversification = "GOOD"

    elif stats.positions >= 3:

        diversification = "AVERAGE"

    else:

        diversification = "POOR"

    # ----------------------------------
    # Result
    # ----------------------------------

    return {

        "score": score,

        "grade": grade,

        "risk": risk,

        "cash_ratio": cash_ratio,

        "diversification": diversification,

    }