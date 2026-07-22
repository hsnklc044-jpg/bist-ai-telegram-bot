"""
QuantBIST RC5
Dashboard View Model
"""

from __future__ import annotations


from dataclasses import dataclass, field
from datetime import datetime


from core.committee.models import (
    CommitteeResult,
)

from core.decision.models import (
    Decision,
)

from core.market.models import (
    MarketStatus,
)

from core.portfolio.models import (
    PortfolioAnalysis,
)





@dataclass(slots=True)
class DashboardModel:
    """
    Complete RC5 Dashboard View Model.

    Used by:

    - Web Dashboard
    - API
    - Reports
    - Telegram

    """



    # =================================================
    # Summary Cards
    # =================================================


    stats: dict = field(

        default_factory=dict,

    )





    # =================================================
    # Portfolio Intelligence
    # =================================================


    portfolio: PortfolioAnalysis | None = None





    # =================================================
    # Market Intelligence
    # =================================================


    market: MarketStatus | None = None





    # =================================================
    # Committee Intelligence
    # =================================================


    committee: CommitteeResult | None = None





    # =================================================
    # Final AI Decision
    # =================================================


    decision: Decision | None = None





    # =================================================
    # Charts
    # =================================================


    charts: dict = field(

        default_factory=dict,

    )





    # =================================================
    # Signals
    # =================================================


    signals: list[dict] = field(

        default_factory=list,

    )





    # =================================================
    # Watchlist
    # =================================================


    watchlist: list[dict] = field(

        default_factory=list,

    )





    # =================================================
    # Metadata
    # =================================================


    updated: datetime | None = None





# =====================================================
# EXPORTS
# =====================================================


__all__ = [

    "DashboardModel",

]