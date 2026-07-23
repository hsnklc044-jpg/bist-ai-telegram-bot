"""
QuantBIST RC7
Dashboard Cards

Dashboard presentation layer.
"""

from __future__ import annotations


from core.analytics.signals import (
    get_top_signals,
)


from core.watchlist.service import (
    get_watchlist_details,
)





# =====================================================
# SUMMARY
# =====================================================


def get_summary_cards(
    stats,
) -> dict:
    """
    Generate dashboard summary cards.

    Stats are calculated once
    by dashboard service.
    """


    return {

        "portfolio":
            stats.portfolio,

        "cash":
            stats.cash,

        "positions":
            stats.positions,

        "top_stock":
            stats.top_stock,

        "sharpe":
            stats.sharpe,

        "win_rate":
            stats.win_rate,

        "profit_factor":
            stats.profit_factor,

        "max_drawdown":
            stats.max_drawdown,

    }





# =====================================================
# AI DECISION CARDS
# =====================================================


def get_ai_cards(
    decision,
) -> dict:
    """
    Generate RC7 AI decision intelligence cards.

    Source:

        Decision Engine RC7

    """


    return {

        # ---------------------------------------------
        # Final Action
        # ---------------------------------------------

        "action":
            decision.action,


        "score":
            decision.score,


        "ai_score":
            decision.ai_score,


        "confidence":
            decision.confidence,



        # ---------------------------------------------
        # Recommendation Layer
        # ---------------------------------------------


        "recommendation":
            getattr(
                decision,
                "recommendation",
                decision.summary,
            ),



        "summary":
            decision.summary,



        # ---------------------------------------------
        # Explanation Layer
        # ---------------------------------------------


        "reasons":
            decision.reasons,


        "warnings":
            decision.warnings,


        "suggestions":
            decision.suggestions,



        "score_breakdown":
            decision.score_breakdown,



        "decision_context":
            decision.decision_context,



        # ---------------------------------------------
        # Technical Intelligence
        # ---------------------------------------------


        "technical_score":
            decision.technical_score,


        "technical_trend":
            decision.technical_trend,


        "rsi":
            decision.rsi,


        "macd_signal":
            decision.macd_signal,



        # ---------------------------------------------
        # Risk Intelligence
        # ---------------------------------------------


        "risk":
            decision.risk_level,


        "risk_score":
            decision.risk_score,



        # ---------------------------------------------
        # Market Intelligence
        # ---------------------------------------------


        "market_status":
            decision.market_status,


        "market_regime":
            decision.market_regime,


        "market_trend":
            decision.market_trend,



        # ---------------------------------------------
        # Portfolio Intelligence
        # ---------------------------------------------


        "portfolio_health":
            decision.portfolio_health,


        "portfolio_grade":
            decision.portfolio_grade,


        "rebalance":
            decision.rebalance_required,

    }





# =====================================================
# SIGNALS
# =====================================================


def get_signals_card() -> list[dict]:
    """
    Dashboard AI signals.
    """


    return get_top_signals()





# =====================================================
# WATCHLIST
# =====================================================


def get_watchlist_card() -> list[dict]:
    """
    Dashboard watchlist intelligence.
    """


    try:

        return get_watchlist_details()


    except Exception:

        return []





# =====================================================
# EXPORTS
# =====================================================


__all__ = [

    "get_summary_cards",

    "get_ai_cards",

    "get_signals_card",

    "get_watchlist_card",

]