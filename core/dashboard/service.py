"""
QuantBIST RC4
Dashboard Service
"""

from __future__ import annotations

from datetime import datetime

from core.ai.dashboard_ai import generate_ai_summary
from core.ai.recommendation_engine import generate_recommendation

from core.dashboard.cards import (
    get_summary_cards,
    get_signals_card,
    get_watchlist_card,
)

from core.dashboard.charts import (
    get_dashboard_charts,
)

from core.market.service import (
    get_market_status,
)


def get_dashboard() -> dict:
    """
    QuantBIST Dashboard verilerini üretir.

    Bu servis yalnızca orchestrator görevi görür.
    """

    # ----------------------------------
    # Dashboard Data
    # ----------------------------------

    stats = get_summary_cards()

    signals = get_signals_card()

    watchlist = get_watchlist_card()

    charts = get_dashboard_charts()

    market = get_market_status()

    # ----------------------------------
    # AI
    # ----------------------------------

    ai = generate_ai_summary(
        stats=stats,
        signals=signals,
    )

    recommendation = generate_recommendation(
        ai,
    )

    # ----------------------------------
    # Dashboard Object
    # ----------------------------------

    dashboard = {

        "stats": stats,

        "signals": signals,

        "watchlist": watchlist,

        "charts": charts,

        "market": market,

        "ai": ai,

        "recommendation": recommendation,

        "updated": datetime.now().strftime(
            "%d.%m.%Y %H:%M"
        ),

    }

    return dashboard