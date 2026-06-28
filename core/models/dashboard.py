"""
QuantBIST Framework
Dashboard View Model
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from core.decision.models import Decision
from core.market.models import MarketStatus
from core.portfolio.models import PortfolioStats


@dataclass(slots=True)
class DashboardModel:
    """
    Complete dashboard view model.

    This is the object returned by the Dashboard
    Service and consumed by the presentation layer.
    """

    stats: PortfolioStats

    market: MarketStatus

    decision: Decision

    signals: list[dict]

    watchlist: list[str]

    charts: dict

    updated: datetime