"""
QuantBIST Framework
Dashboard Service
"""

from __future__ import annotations

from datetime import datetime

from core.dashboard.cards import (
    get_signals_card,
    get_summary_cards,
    get_watchlist_card,
)

from core.dashboard.charts import (
    get_dashboard_charts,
)

from core.decision.engine import (
    generate_decision,
)

from core.infrastructure.logger import (
    get_logger,
)

from core.market.service import (
    get_market_status,
)

from core.models.dashboard import (
    DashboardModel,
)

logger = get_logger(__name__)


def get_dashboard() -> DashboardModel:
    """
    Build complete dashboard model.

    Returns
    -------
    DashboardModel
    """

    logger.info(
        "Building dashboard model..."
    )

    # --------------------------------------------
    # Portfolio
    # --------------------------------------------

    stats = get_summary_cards()

    # --------------------------------------------
    # Market
    # --------------------------------------------

    market = get_market_status()

    # --------------------------------------------
    # Decision
    # --------------------------------------------

    decision = generate_decision(
        stats,
    )

    # --------------------------------------------
    # Dashboard Components
    # --------------------------------------------

    signals = get_signals_card()

    watchlist = get_watchlist_card()

    charts = get_dashboard_charts()

    dashboard = DashboardModel(

        stats=stats,

        market=market,

        decision=decision,

        signals=signals,

        watchlist=watchlist,

        charts=charts,

        updated=datetime.now(),

    )

    logger.info(
        "Dashboard model ready."
    )

    return dashboard