"""
QuantBIST RC5
Dashboard Cards
"""

from __future__ import annotations


from core.analytics.signals import (
    get_top_signals,
)


from core.portfolio.dashboard_data import (
    get_dashboard_stats,
)


from core.watchlist.service import (
    get_watchlist_details,
)





# =====================================================
# SUMMARY
# =====================================================


def get_summary_cards() -> dict:
    """
    Generate dashboard summary cards.
    """


    stats = get_dashboard_stats()



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
    Generate RC5 AI intelligence cards.

    Source:

        Decision Engine

    Includes:

        - Action
        - AI Score
        - Confidence
        - Technical Score
        - Risk
        - Market Regime

    """


    return {


        "action":

            decision.action,



        "ai_score":

            decision.ai_score,



        "confidence":

            decision.confidence,



        "technical_score":

            decision.technical_score,



        "technical_trend":

            decision.technical_trend,



        "rsi":

            decision.rsi,



        "macd_signal":

            decision.macd_signal,



        "risk":

            decision.risk_level,



        "risk_score":

            decision.risk_score,



        "market_regime":

            decision.market_regime,



        "market_trend":

            decision.market_trend,



        "rebalance":

            decision.rebalance_required,



        "summary":

            decision.summary,

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