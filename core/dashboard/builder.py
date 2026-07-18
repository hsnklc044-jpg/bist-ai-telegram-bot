"""
QuantBIST Framework
Dashboard Builder
"""

from __future__ import annotations

from core.charts.service import (
    get_dashboard_charts,
)

from core.models.context import (
    DashboardContext,
)

from core.models.dashboard import (
    DashboardModel,
)


def build_dashboard(
    context: DashboardContext,
) -> DashboardModel:
    """
    Convert DashboardContext into DashboardModel.
    """

    context.charts = get_dashboard_charts(

        risk_score=context.risk_score,

        ai_score=context.ai_score,

    )

    return DashboardModel(

        stats=context.stats,

        portfolio=context.portfolio,

        market=context.market,

        committee=context.committee,

        decision=context.decision,

        charts=context.charts,

        signals=context.signals,

        watchlist=context.watchlist,

        updated=context.updated,

    )


__all__ = [

    "build_dashboard",

]