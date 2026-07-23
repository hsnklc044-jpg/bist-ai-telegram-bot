"""
QuantBIST RC6
Dashboard Intelligence Service
"""

from __future__ import annotations


from datetime import datetime


from core.charts.service import (
    get_dashboard_charts,
)


from core.dashboard.cards import (
    get_ai_cards,
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
    Build complete QuantBIST dashboard.

    RC6 Flow:

        Portfolio Stats
              |
        Portfolio Intelligence
              |
        Market Intelligence
              |
        Decision Intelligence
              |
        Dashboard

    Committee is executed only inside Decision Engine.

    """



    logger.info(

        "Dashboard generation started."

    )



    try:



        # -----------------------------------------
        # Portfolio Statistics
        # -----------------------------------------


        portfolio_stats = get_dashboard_stats()





        # -----------------------------------------
        # Portfolio Intelligence
        # -----------------------------------------


        portfolio = get_portfolio_analysis(

            portfolio_stats,

        )





        # -----------------------------------------
        # Market Intelligence
        # -----------------------------------------


        market = get_market_status()





        # -----------------------------------------
        # Decision Intelligence
        #
        # Committee runs here once.
        #
        # -----------------------------------------


        decision = get_decision(

            portfolio_stats,

            portfolio,

            market,

        )





        # -----------------------------------------
        # Committee
        #
        # Decision model currently keeps
        # committee summary fields only.
        #
        # -----------------------------------------


        committee = None





        # -----------------------------------------
        # Charts
        # -----------------------------------------


        charts = get_dashboard_charts(

            risk_score=decision.risk_score,

            ai_score=decision.ai_score,

        )





        # -----------------------------------------
        # Dashboard Model
        # -----------------------------------------


        dashboard = DashboardModel(



            stats=get_summary_cards(

                portfolio_stats,

            ),



            portfolio=portfolio,



            market=market,



            committee=committee,



            decision=decision,



            charts=charts,



            signals=get_signals_card(),



            watchlist=get_watchlist_card(),



            updated=datetime.now(),

        )





        logger.info(

            "Dashboard ready | Action=%s | AI=%d | Confidence=%d",

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







# =====================================================
# EXPORTS
# =====================================================


__all__ = [

    "get_dashboard",

]