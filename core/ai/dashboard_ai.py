"""
QuantBIST RC4
Dashboard AI Engine
"""

from __future__ import annotations

from core.portfolio.analyzer import analyze_portfolio


def generate_ai_summary(
    stats,
    signals: list[dict],
) -> dict:
    """
    Dashboard AI Summary.

    Dashboard için tüm AI verilerini üretir.
    """

    analysis = analyze_portfolio(stats)

    health = analysis["health"]

    risk = analysis["risk"]

    optimization = analysis["optimization"]

    rebalance = analysis["rebalance"]

    # -----------------------------
    # Best Opportunity
    # -----------------------------

    if signals:

        best = max(
            signals,
            key=lambda x: x["score"],
        )

        best_symbol = best["symbol"]

    else:

        best_symbol = "-"

    # -----------------------------
    # Worst Position
    # -----------------------------

    worst_symbol = optimization["smallest_position"]

    # -----------------------------
    # Recommendation
    # -----------------------------

    if rebalance["needs_rebalance"]:

        recommendation = "REBALANCING RECOMMENDED"

    elif risk["level"] == "VERY HIGH":

        recommendation = "REDUCE RISK"

    elif risk["level"] == "HIGH":

        recommendation = "HOLD"

    elif health["score"] >= 90:

        recommendation = "STRONG BUY"

    elif health["score"] >= 80:

        recommendation = "BUY"

    elif health["score"] >= 70:

        recommendation = "WATCH"

    else:

        recommendation = "HOLD"

    return {

        "risk": risk["level"],

        "risk_score": risk["score"],

        "risk_comment": risk["comment"],

        "cash_ratio": health["cash_ratio"],

        "portfolio_health": health["score"],

        "portfolio_grade": health["grade"],

        "diversification": health["diversification"],

        "best": best_symbol,

        "worst": worst_symbol,

        "largest_position": optimization["largest_position"],

        "largest_weight": optimization["largest_weight"],

        "rebalance": rebalance["needs_rebalance"],

        "rebalance_summary": rebalance["summary"],

        "recommendation": recommendation,

    }
