"""
QuantBIST Framework
Decision Engine
"""

from __future__ import annotations

from core.ai.scoring import calculate_score
from core.decision.models import Decision
from core.infrastructure.exceptions import DecisionError
from core.infrastructure.logger import get_logger
from core.market.models import MarketStatus
from core.portfolio.models import PortfolioAnalysis

logger = get_logger(__name__)


def _calculate_priority(score: int) -> str:
    if score >= 90:
        return "LOW"
    if score >= 75:
        return "MEDIUM"
    if score >= 55:
        return "HIGH"
    return "CRITICAL"


def _calculate_action(score: int, regime: str) -> str:
    regime = regime.upper()
    if score >= 90 and regime == "RISK_ON":
        return "STRONG BUY"
    if score >= 75:
        return "BUY"
    if score >= 55:
        return "WATCH"
    if score >= 35:
        return "REDUCE"
    return "SELL"


def _build_summary(action: str, score: int) -> str:
    return f"{action} recommendation generated (AI Score: {score}/100)."


def generate_decision(
    portfolio: PortfolioAnalysis,
    market: MarketStatus,
) -> Decision:
    logger.info("Decision Engine started.")
    try:
        score = calculate_score(portfolio=portfolio, market=market)

        confidence = min(99, max(50, round((score + portfolio.health.score) / 2)))

        action = _calculate_action(score, market.regime.status)
        priority = _calculate_priority(score)

        reasons = [
            f"Portfolio Grade: {portfolio.health.grade}",
            f"Market Regime: {market.regime.status}",
        ]

        suggestions = list(portfolio.optimization.suggestions)

        warnings = []
        if portfolio.risk.level.upper() in ("HIGH", "CRITICAL"):
            warnings.append("Portfolio risk is elevated.")
        if market.regime.status.upper() == "RISK_OFF":
            warnings.append("Risk-Off market conditions.")

        decision = Decision(
            action=action,
            score=score,
            confidence=confidence,
            priority=priority,
            summary=_build_summary(action, score),
            portfolio_health=portfolio.health.score,
            portfolio_grade=portfolio.health.grade,
            risk_level=portfolio.risk.level,
            market_status=market.status,
            market_trend=market.trend,
            market_regime=market.regime.status,
            best_symbol=portfolio.stats.top_stock,
            worst_symbol="-",
            rebalance_required=portfolio.rebalance.needs_rebalance,
            reasons=reasons,
            suggestions=suggestions,
            warnings=warnings,
        )

        logger.info("Decision generated: %s (%d)", decision.action, decision.score)
        return decision

    except DecisionError:
        raise
    except Exception as exc:
        logger.exception("Decision Engine failed.")
        raise DecisionError(str(exc)) from exc
