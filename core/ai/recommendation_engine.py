"""
QuantBIST RC4
AI Recommendation Engine
"""

from __future__ import annotations

from core.decision.models import Decision


def generate_recommendation(
    portfolio: dict,
    market: dict,
) -> Decision:
    """
    QuantBIST AI Decision Engine.

    Portfolio Analyzer ve Market Analyzer çıktılarından
    nihai yatırım kararını üretir.
    """

    # --------------------------------------------------
    # Portfolio
    # --------------------------------------------------

    health = portfolio["health"]
    risk = portfolio["risk"]
    optimization = portfolio["optimization"]
    rebalance = portfolio["rebalance"]

    # --------------------------------------------------
    # Market
    # --------------------------------------------------

    trend = market["trend"]
    regime = market["regime"]
    status = market["status"]

    # --------------------------------------------------
    # Initial Score
    # --------------------------------------------------

    score = 100

    reasons = []

    suggestions = []

    warnings = []

    # --------------------------------------------------
    # Portfolio Health
    # --------------------------------------------------

    if health["score"] < 70:

        score -= 25

        reasons.append(
            "Portfolio health is below target."
        )

    elif health["score"] < 85:

        score -= 10

        reasons.append(
            "Portfolio health can be improved."
        )

    # --------------------------------------------------
    # Risk
    # --------------------------------------------------

    if risk["level"] == "VERY HIGH":

        score -= 30

        warnings.append(
            "Portfolio risk is VERY HIGH."
        )

    elif risk["level"] == "HIGH":

        score -= 20

        warnings.append(
            "Portfolio risk is HIGH."
        )

    elif risk["level"] == "MEDIUM":

        score -= 10

    # --------------------------------------------------
    # Concentration
    # --------------------------------------------------

    if optimization["concentration_risk"]:

        score -= 15

        warnings.append(

            f"Large concentration in "

            f"{optimization['largest_position']}."

        )

    # --------------------------------------------------
    # Rebalance
    # --------------------------------------------------

    if rebalance["needs_rebalance"]:

        score -= 10

        suggestions.extend(

            rebalance["summary"].split(",")

        )

    # --------------------------------------------------
    # Market Trend
    # --------------------------------------------------

    if trend == "BULLISH":

        score += 5

    elif trend == "BEARISH":

        score -= 10

        warnings.append(
            "Market trend is bearish."
        )

    # --------------------------------------------------
    # Market Regime
    # --------------------------------------------------

    if regime == "RISK_OFF":

        score -= 10

        warnings.append(
            "Risk-Off market regime."
        )

    elif regime == "RISK_ON":

        score += 5

    # --------------------------------------------------
    # Normalize
    # --------------------------------------------------

    score = max(
        0,
        min(
            100,
            int(score),
        ),
    )

    # --------------------------------------------------
    # Decision
    # --------------------------------------------------

    if score >= 90:

        action = "STRONG BUY"
        confidence = 95
        priority = "LOW"

    elif score >= 80:

        action = "BUY"
        confidence = 90
        priority = "LOW"

    elif score >= 70:

        action = "WATCH"
        confidence = 80
        priority = "MEDIUM"

    elif score >= 55:

        action = "REBALANCE"
        confidence = 75
        priority = "HIGH"

    else:

        action = "REDUCE RISK"
        confidence = 95
        priority = "CRITICAL"

    # --------------------------------------------------
    # Summary
    # --------------------------------------------------

    summary = (

        f"{action} | "

        f"Score: {score}/100 | "

        f"Market: {trend}"

    )

    # --------------------------------------------------
    # Decision Model
    # --------------------------------------------------

    return Decision(

        action=action,

        score=score,

        confidence=confidence,

        priority=priority,

        summary=summary,

        portfolio_health=health["score"],

        portfolio_grade=health["grade"],

        risk_level=risk["level"],

        market_status=status,

        market_trend=trend,

        market_regime=regime,

        best_symbol=optimization["largest_position"],

        worst_symbol=optimization["smallest_position"],

        rebalance_required=rebalance["needs_rebalance"],

        reasons=reasons,

        suggestions=suggestions,

        warnings=warnings,

    )