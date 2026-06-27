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

from core.portfolio.analyzer import (
    analyze_portfolio,
)


def get_dashboard() -> dict:
    """
    QuantBIST RC4 Dashboard Service.

    Dashboard için gerekli tüm verileri üretir.
    Bu servis yalnızca orchestrator görevi görür.
    """

    # -------------------------------------------------
    # Portfolio
    # -------------------------------------------------

    stats = get_summary_cards()

    # -------------------------------------------------
    # Signals
    # -------------------------------------------------

    signals = get_signals_card()

    # -------------------------------------------------
    # Watchlist
    # -------------------------------------------------

    watchlist = get_watchlist_card()

    # -------------------------------------------------
    # Charts
    # -------------------------------------------------

    charts = get_dashboard_charts()

    # -------------------------------------------------
    # Market
    # -------------------------------------------------

    market = get_market_status()

    # -------------------------------------------------
    # Portfolio Analysis
    # -------------------------------------------------

    analysis = analyze_portfolio(stats)

    # -------------------------------------------------
    # Dashboard AI
    # -------------------------------------------------

    ai = generate_ai_summary(
        stats=stats,
        signals=signals,
    )

    # -------------------------------------------------
    # Recommendation Engine
    # -------------------------------------------------

    decision = generate_recommendation(
        analysis,
    )

    # -------------------------------------------------
    # Dashboard Object
    # -------------------------------------------------

    dashboard = {

        "stats": stats,

        "signals": signals,

        "watchlist": watchlist,

        "charts": charts,

        "market": market,

        "analysis": analysis,

        "ai": ai,

        "decision": decision,

        "recommendation": decision["summary"],

        "updated": datetime.now().strftime(
            "%d.%m.%Y %H:%M"
        ),

    }

    return dashboard