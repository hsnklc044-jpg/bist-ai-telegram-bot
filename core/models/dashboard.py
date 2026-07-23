"""
QuantBIST RC6
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
    Complete QuantBIST RC6 Dashboard View Model.

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





    # =================================================
    # Final Decision
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
    # Helpers
    # =================================================


    @property
    def summary(self) -> dict:
        """
        Quick dashboard summary.
        """


        if self.decision is None:

            return {}



        return {

            "action":
                self.decision.action,


            "score":
                self.decision.ai_score,


            "confidence":
                self.decision.confidence,


            "risk":
                self.decision.risk_level,


            "market":
                self.decision.market_regime,


        }





    @property
    def summary_dict(self) -> dict:
        """
        Backward compatibility alias.
        """


        return self.summary







# =====================================================
# EXPORTS
# =====================================================


__all__ = [

    "DashboardModel",

]