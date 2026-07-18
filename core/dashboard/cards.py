"""
QuantBIST Framework
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
    get_watchlist,
)


# =====================================================
# SUMMARY
# =====================================================

def get_summary_cards():
    """
    Portfolio summary cards.

    Returns
    -------
    PortfolioStats
    """

    return get_dashboard_stats()


# =====================================================
# SIGNALS
# =====================================================

def get_signals_card() -> list[dict]:
    """
    Dashboard signal list.

    Returns
    -------
    list[dict]
    """

    return get_top_signals()


# =====================================================
# WATCHLIST
# =====================================================

def get_watchlist_card() -> list[str]:
    """
    Dashboard watchlist.

    Returns
    -------
    list[str]
    """

    watchlist = get_watchlist()

    if not watchlist:
        return []

    # watchlist.service farklı formatlar döndürse bile
    # dashboard için standart liste üret.
    result: list[str] = []

    for item in watchlist:

        if isinstance(item, str):

            result.append(item)

        elif isinstance(item, dict):

            symbol = item.get("symbol")

            if symbol:
                result.append(symbol)

    return result


# =====================================================
# EXPORTS
# =====================================================

__all__ = [

    "get_summary_cards",

    "get_signals_card",

    "get_watchlist_card",

]