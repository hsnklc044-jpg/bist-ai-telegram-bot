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
    Dashboard AI Summary üretir.
    """

    # ----------------------------------
    # Portfolio Analysis
    # ----------------------------------

    analysis = analyze_portfolio(stats)

    health = analysis["health"]

    risk = analysis["risk"]

    # ----------------------------------
    # Best Opportunity
    # ----------------------------------

    if signals:

        best = signals[0]["symbol"]

        best_score = signals[0]["score"]

    else:

        best = "-"

        best_score = 0

    # ----------------------------------
    # Worst Position
    # Sprint 12 sonunda gerçek hesaplanacak
    # ----------------------------------

    worst = "-"

    # ----------------------------------
    # Recommendation
    # ----------------------------------

    if risk["level"] == "VERY HIGH":

        recommendation = "REDUCE RISK"

    elif risk["level"] == "HIGH":

        recommendation = "HOLD"

    elif best_score >= 80:

        recommendation = "STRONG BUY"

    elif best_score >= 70:

        recommendation = "BUY"

    elif best_score >= 60:

        recommendation = "WATCH"

    else:

        recommendation = "HOLD"

    # ----------------------------------
    # Result
    # ----------------------------------

    return {

        "risk": risk["level"],

        "risk_score": risk["score"],

        "risk_comment": risk["comment"],

        "best": best,

        "worst": worst,

        "cash_ratio": health["cash_ratio"],

        "recommendation": recommendation,

        "portfolio_health": health["score"],

        "portfolio_grade": health["grade"],

        "diversification": health["diversification"],

    }