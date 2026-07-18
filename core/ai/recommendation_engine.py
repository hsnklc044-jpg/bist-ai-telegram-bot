"""
QuantBIST Framework
AI Recommendation Engine
"""

from __future__ import annotations

from core.decision.models import Decision


# =====================================================
# HELPERS
# =====================================================

def _build_overview(
    decision: Decision,
) -> list[str]:
    """
    Executive overview.
    """

    overview: list[str] = []

    overview.append(
        f"Recommendation : {decision.action}"
    )

    overview.append(
        f"AI Score : {decision.score}/100"
    )

    overview.append(
        f"Confidence : {decision.confidence}%"
    )

    overview.append(
        f"Priority : {decision.priority}"
    )

    return overview


# =====================================================
# PORTFOLIO
# =====================================================

def _portfolio_section(
    decision: Decision,
) -> list[str]:
    """
    Portfolio explanation.
    """

    lines: list[str] = []

    lines.append(
        f"Portfolio Grade : {decision.portfolio_grade}"
    )

    lines.append(
        f"Portfolio Health : {decision.portfolio_health:.1f}"
    )

    lines.append(
        f"Risk Level : {decision.risk_level}"
    )

    if decision.rebalance_required:

        lines.append(
            "Portfolio rebalancing is recommended."
        )

    return lines


# =====================================================
# MARKET
# =====================================================

def _market_section(
    decision: Decision,
) -> list[str]:
    """
    Market explanation.
    """

    return [

        f"Market Trend : {decision.market_trend}",

        f"Market Regime : {decision.market_regime}",

        f"Market Status : {decision.market_status}",

    ]


# =====================================================
# REASONS
# =====================================================

def _reason_section(
    decision: Decision,
) -> list[str]:
    """
    Decision reasons.
    """

    if decision.reasons:

        return decision.reasons

    return [

        "No additional explanation available."

    ]


# =====================================================
# SUGGESTIONS
# =====================================================

def _suggestion_section(
    decision: Decision,
) -> list[str]:
    """
    Optimization suggestions.
    """

    return decision.suggestions


# =====================================================
# WARNINGS
# =====================================================

def _warning_section(
    decision: Decision,
) -> list[str]:
    """
    Risk warnings.
    """

    return decision.warnings


# =====================================================
# PUBLIC API
# =====================================================

def generate_recommendation(
    decision: Decision,
) -> str:
    """
    Generate a human-readable recommendation.

    Parameters
    ----------
    decision
        Final Decision model.

    Returns
    -------
    str
    """

    sections: list[str] = []

    sections.extend(
        _build_overview(
            decision,
        )
    )

    sections.append("")

    sections.append("Portfolio")

    sections.extend(

        _portfolio_section(
            decision,
        )

    )

    sections.append("")

    sections.append("Market")

    sections.extend(

        _market_section(
            decision,
        )

    )

    sections.append("")

    sections.append("Reasons")

    sections.extend(

        _reason_section(
            decision,
        )

    )

    if decision.suggestions:

        sections.append("")

        sections.append(
            "Suggestions"
        )

        sections.extend(

            _suggestion_section(
                decision,
            )

        )

    if decision.warnings:

        sections.append("")

        sections.append(
            "Warnings"
        )

        sections.extend(

            _warning_section(
                decision,
            )

        )

    return "\n".join(
        sections
    )