"""
QuantBIST RC7
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
    Complete QuantBIST RC7 Dashboard View Model.

    Used by:

    - Web Dashboard
    - API
    - Reports
    - Telegram

    """



    # =================================================
    # Summary Statistics
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
    # Investment Committee
    # =================================================


    committee: CommitteeResult | None = None



    committee_card: dict = field(

        default_factory=dict,

    )





    # =================================================
    # Decision Intelligence
    # =================================================


    decision: Decision | None = None





    # =================================================
    # AI Cards
    # =================================================


    ai: dict = field(

        default_factory=dict,

    )





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





    # =================================================
    # AI INTELLIGENCE
    # =================================================


    @property
    def intelligence(self) -> dict:


        if self.decision is None:

            return {}



        if hasattr(

            self.decision,

            "intelligence_dict",

        ):

            return self.decision.intelligence_dict



        return {}







    # =================================================
    # SUMMARY
    # =================================================


    @property
    def summary(self) -> dict:


        if self.decision is None:

            return {}



        return {


            "action":

                self.decision.action,


            "score":

                self.decision.ai_score,


            "confidence":

                self.decision.confidence,


            "priority":

                self.decision.priority,


            "risk":

                self.decision.risk_level,


            "market":

                self.decision.market_regime,


            "trend":

                self.decision.market_trend,


            "rebalance":

                self.decision.rebalance_required,


        }






    @property
    def summary_dict(self) -> dict:

        return self.summary






    # =================================================
    # STATUS
    # =================================================


    @property
    def ready(self) -> bool:


        return (

            self.decision is not None

            and

            self.market is not None

            and

            self.portfolio is not None

        )






# =====================================================
# EXPORTS
# =====================================================


__all__ = [

    "DashboardModel",

]