"""
QuantBIST Framework
Decision Warning Engine
"""

from __future__ import annotations

from core.market.models import MarketStatus
from core.portfolio.models import PortfolioAnalysis


# =====================================================
# AI WARNINGS
# =====================================================

def _ai_warnings(
    ai_score: int,
) -> list[str]:
    """
    AI related warnings.
    """

    warnings: list[str] = []

    if ai_score < 30:

        warnings.append(
            "AI score is critically low."
        )

    elif ai_score < 50:

        warnings.append(
            "AI score is below the preferred threshold."
        )

    return warnings


# =====================================================
# PORTFOLIO HEALTH
# =====================================================

def _health_warnings(
    portfolio: PortfolioAnalysis,
) -> list[str]:
    """
    Portfolio health warnings.
    """

    warnings: list[str] = []

    score = portfolio.health.score

    if score < 50:

        warnings.append(
            "Portfolio health is critically low."
        )

    elif score < 65:

        warnings.append(
            "Portfolio health needs improvement."
        )

    return warnings


# =====================================================
# RISK
# =====================================================

def _risk_warnings(
    portfolio: PortfolioAnalysis,
) -> list[str]:
    """
    Portfolio risk warnings.
    """

    warnings: list[str] = []

    risk = portfolio.risk.level.upper()

    if risk == "HIGH":

        warnings.append(
            "Portfolio risk is high."
        )

    elif risk == "CRITICAL":

        warnings.append(
            "Portfolio risk is critical."
        )

    return warnings


# =====================================================
# OPTIMIZATION
# =====================================================

def _optimization_warnings(
    portfolio: PortfolioAnalysis,
) -> list[str]:
    """
    Portfolio optimization warnings.
    """

    warnings: list[str] = []

    optimization = portfolio.optimization

    if optimization.rebalance:

        warnings.append(
            "Portfolio rebalancing is required."
        )

    if optimization.concentration_risk:

        warnings.append(
            "Portfolio concentration exceeds the configured limit."
        )

    if len(optimization.suggestions) >= 5:

        warnings.append(
            "Multiple optimization opportunities detected."
        )

    if hasattr(
        optimization,
        "health_score",
    ):

        if optimization.health_score < 60:

            warnings.append(
                "Portfolio optimization quality is weak."
            )

    return warnings


# =====================================================
# MARKET
# =====================================================

def _market_warnings(
    market: MarketStatus,
) -> list[str]:
    """
    Market related warnings.
    """

    warnings: list[str] = []

    regime = market.regime.status.upper()

    if regime == "RISK_OFF":

        warnings.append(
            "Market is currently in Risk-Off mode."
        )

    breadth = market.breadth.status.upper()

    if breadth == "NEGATIVE":

        warnings.append(
            "Market breadth is negative."
        )

    sentiment = market.sentiment.status.upper()

    if sentiment == "FEAR":

        warnings.append(
            "Investor sentiment indicates fear."
        )

    volatility = str(
        market.volatility,
    ).upper()

    if volatility == "HIGH":

        warnings.append(
            "Market volatility is high."
        )

    return warnings


# =====================================================
# COMBINED CONDITIONS
# =====================================================

def _combined_warnings(
    ai_score: int,
    portfolio: PortfolioAnalysis,
    market: MarketStatus,
) -> list[str]:
    """
    Multi-factor warnings.
    """

    warnings: list[str] = []

    risk = portfolio.risk.level.upper()

    regime = market.regime.status.upper()

    breadth = market.breadth.status.upper()

    sentiment = market.sentiment.status.upper()

    if (
        risk in (
            "HIGH",
            "CRITICAL",
        )
        and regime == "RISK_OFF"
    ):

        warnings.append(
            "High-risk portfolio in a Risk-Off market."
        )

    if (
        breadth == "NEGATIVE"
        and sentiment == "FEAR"
    ):

        warnings.append(
            "Weak market breadth combined with fearful sentiment."
        )

    if (
        ai_score < 50
        and portfolio.health.score < 60
    ):

        warnings.append(
            "AI score and portfolio health are both weak."
        )

    if (
        portfolio.optimization.rebalance
        and regime == "RISK_OFF"
    ):

        warnings.append(
            "Portfolio should be rebalanced under defensive market conditions."
        )

    return warnings


# =====================================================
# PUBLIC API
# =====================================================

def build_warnings(
    ai_score: int,
    portfolio: PortfolioAnalysis,
    market: MarketStatus,
) -> list[str]:
    """
    Build complete warning list.
    """

    warnings: list[str] = []

    warnings.extend(
        _ai_warnings(
            ai_score,
        )
    )

    warnings.extend(
        _health_warnings(
            portfolio,
        )
    )

    warnings.extend(
        _risk_warnings(
            portfolio,
        )
    )

    warnings.extend(
        _optimization_warnings(
            portfolio,
        )
    )

    warnings.extend(
        _market_warnings(
            market,
        )
    )

    warnings.extend(
        _combined_warnings(
            ai_score,
            portfolio,
            market,
        )
    )

    # Remove duplicates while preserving order

    unique: list[str] = []

    for warning in warnings:

        if warning not in unique:

            unique.append(
                warning
            )

    return unique