"""
QuantBIST RC4
Portfolio Risk Engine
"""

from __future__ import annotations

from core.portfolio.models import PortfolioStats


def calculate_risk(
    stats: PortfolioStats,
) -> dict:
    """
    Portföy risk analizini yapar.

    Returns
    -------
    dict
        {
            "score": int,
            "level": str,
            "cash_ratio": float,
            "comment": str,
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
    # Risk Score
    # ----------------------------------

    score = 0

    # Max Drawdown

    if stats.max_drawdown > 20:

        score += 35

    elif stats.max_drawdown > 10:

        score += 20

    else:

        score += 10

    # Sharpe Ratio

    if stats.sharpe < 1:

        score += 30

    elif stats.sharpe < 2:

        score += 20

    else:

        score += 10

    # Win Rate

    if stats.win_rate < 50:

        score += 20

    elif stats.win_rate < 60:

        score += 10

    # Cash Ratio

    if cash_ratio < 5:

        score += 20

    elif cash_ratio < 10:

        score += 10

    # Position Count

    if stats.positions < 3:

        score += 15

    elif stats.positions < 6:

        score += 8

    # ----------------------------------
    # Risk Level
    # ----------------------------------

    if score <= 30:

        level = "LOW"

    elif score <= 50:

        level = "MEDIUM"

    elif score <= 70:

        level = "HIGH"

    else:

        level = "VERY HIGH"

    # ----------------------------------
    # Comment
    # ----------------------------------

    comments = {
        "LOW": (
            "Portfolio risk is low. "
            "Current allocation appears balanced."
        ),
        "MEDIUM": (
            "Portfolio risk is moderate. "
            "Monitor existing positions."
        ),
        "HIGH": (
            "Portfolio risk is elevated. "
            "Consider reducing exposure."
        ),
        "VERY HIGH": (
            "Portfolio risk is very high. "
            "Immediate review is recommended."
        ),
    }

    return {

        "score": score,

        "level": level,

        "cash_ratio": cash_ratio,

        "comment": comments[level],

    }