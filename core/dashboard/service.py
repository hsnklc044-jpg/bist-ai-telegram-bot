"""
QuantBIST RC7
Dashboard Intelligence Service
"""

from __future__ import annotations

from datetime import datetime

from core.charts.service import (
    get_dashboard_charts,
)
from core.dashboard.cards import (
    get_ai_cards,
    get_committee_card,
    get_signals_card,
    get_summary_cards,
    get_watchlist_card,
)
from core.decision.service import (
    get_decision,
)
from core.infrastructure.exceptions import (
    DashboardError,
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
from core.portfolio.dashboard_data import (
    get_dashboard_stats,
)
from core.portfolio.service import (
    get_portfolio_analysis,
)

logger = get_logger(__name__)







# =====================================================
# PUBLIC API
# =====================================================


def get_dashboard() -> DashboardModel:
    """
    Build complete QuantBIST RC7 dashboard.
    """



    logger.info(
        "Dashboard generation started."
    )



    try:



        # Portfolio Statistics

        portfolio_stats = get_dashboard_stats()



        # Portfolio Intelligence

        portfolio = get_portfolio_analysis(

            portfolio_stats,

        )



        # Market Intelligence

        market = get_market_status()



        # Decision Intelligence

        decision = get_decision(

            portfolio_stats,

            portfolio,

            market,

        )



        # Committee Card

        committee_card = get_committee_card(

            decision,

        )



        # Charts

        charts = get_dashboard_charts(

            risk_score=

                decision.risk_score,


            ai_score=

                decision.ai_score,

        )



        # Cards

        summary_cards = get_summary_cards(

            portfolio_stats,

        )



        ai_cards = get_ai_cards(

            decision,

        )



        signals = get_signals_card()



        watchlist = get_watchlist_card()





        # Dashboard Model

        dashboard = DashboardModel(


            stats=

                summary_cards,


            portfolio=

                portfolio,


            market=

                market,


            committee=

                decision.committee,


            decision=

                decision,


            ai=

                ai_cards,


            charts=

                charts,


            signals=

                signals,


            watchlist=

                watchlist,


            updated=

                datetime.now(),

        )



        # Dynamic presentation field

        dashboard.committee_card = committee_card



        logger.info(

            "Dashboard ready | Action=%s AI=%s Confidence=%s",

            decision.action,

            decision.ai_score,

            decision.confidence,

        )



        return dashboard





    except Exception as exc:


        logger.exception(

            "Dashboard generation failed."

        )


        raise DashboardError(

            str(exc)

        ) from exc








__all__ = [

    "get_dashboard",

]