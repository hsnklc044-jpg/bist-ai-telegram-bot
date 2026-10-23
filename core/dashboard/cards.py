"""
QuantBIST RC7
Dashboard Cards

Presentation layer for Dashboard.
"""

from __future__ import annotations

from core.analytics.signals import (
    get_top_signals,
)
from core.watchlist.service import (
    get_watchlist_details,
)

# =====================================================
# SUMMARY CARDS
# =====================================================


def get_summary_cards(
    stats,
) -> dict:
    """
    Portfolio summary presentation card.
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
# AI DECISION CARD
# =====================================================


def get_ai_cards(
    decision,
) -> dict:
    """
    AI decision presentation card.
    """


    if decision is None:

        return {}



    return {


        "action":

            decision.action,



        "score":

            decision.ai_score,



        "confidence":

            decision.confidence,



        "recommendation":

            decision.recommendation,



        "risk":

            decision.risk_level,



        "risk_score":

            decision.risk_score,



        "market_trend":

            decision.market_trend,



        "market_regime":

            decision.market_regime,



        "portfolio_health":

            decision.portfolio_health,



        "portfolio_grade":

            getattr(

                decision,

                "portfolio_grade",

                "",

            ),



        "rebalance":

            decision.rebalance_required,



        "reasons":

            decision.reasons,



        "warnings":

            decision.warnings,



        "suggestions":

            getattr(

                decision,

                "suggestions",

                [],

            ),


    }





# =====================================================
# COMMITTEE CARD
# =====================================================


def get_committee_card(
    decision,
) -> dict:
    """
    Investment committee presentation card.

    RC7:
    Committee data is transferred
    through Decision object.
    """


    if decision is None:

        return {}



    return {


        "action":

            getattr(

                decision,

                "committee_action",

                "",

            ),



        "score":

            getattr(

                decision,

                "committee_score",

                0,

            ),



        "consensus":

            getattr(

                decision,

                "committee_consensus",

                0,

            ),



        "confidence":

            getattr(

                decision,

                "confidence",

                0,

            ),



        "priority":

            getattr(

                decision,

                "priority",

                "",

            ),


    }





# =====================================================
# SIGNALS
# =====================================================


def get_signals_card() -> list[dict]:
    """
    AI stock signals.
    """


    try:

        return get_top_signals()



    except Exception:

        return []







# =====================================================
# WATCHLIST
# =====================================================


def get_watchlist_card() -> list[dict]:
    """
    Watchlist intelligence.
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


    "get_committee_card",


    "get_signals_card",


    "get_watchlist_card",


]