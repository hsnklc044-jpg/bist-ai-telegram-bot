"""
QuantBIST RC4
Dashboard Service
"""

from __future__ import annotations

from core.portfolio.dashboard_data import (
    get_dashboard_stats,
)

from core.analytics.signals import (
    get_top_signals,
)

from core.watchlist.service import (
    get_watchlist,
)


def get_dashboard():

    stats = get_dashboard_stats()

    signals = get_top_signals()

    # Dashboard için örnek kullanıcı.
    # İleride giriş sistemi geldiğinde
    # gerçek chat_id kullanılacak.
    watchlist = get_watchlist(0)

    return {

        "stats": stats,

        "signals": signals[:5],

        "watchlist": watchlist,

    }