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

    "get_signals_card",

    "get_watchlist_card",

]