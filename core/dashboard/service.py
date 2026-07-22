"""
QuantBIST RC5
Dashboard Intelligence Service
"""

from __future__ import annotations


from datetime import datetime


from core.charts.service import (
    get_dashboard_charts,
)


from core.committee.service import (
    get_committee_decision,
)


from core.dashboard.cards import (
    get_signals_card,
    get_summary_cards,
    get_watchlist_card,
)


from core.decision.builder import (
    build_decision,
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
    Build complete RC5 dashboard.

    Flow:

        Portfolio Stats
              ↓
        Portfolio Intelligence
              ↓
        Market Intelligence
              ↓
        Investment Committee
              ↓
        Final AI Decision
              ↓
        Dashboard

    """



    logger.info(

        "Dashboard generation started."

    )



    try:



        # -----------------------------------------
        # Portfolio
        # -----------------------------------------


        portfolio_stats = get_dashboard_stats()



        portfolio = get_portfolio_analysis(

            portfolio_stats,

        )





        # -----------------------------------------
        # Market
        # -----------------------------------------


        market = get_market_status()





        # -----------------------------------------
        # Committee
        # -----------------------------------------


        committee = get_committee_decision(

            portfolio,

            market,

        )





        # -----------------------------------------
        # Final Decision
        # -----------------------------------------


        decision = build_decision(

            committee=committee,

            portfolio=portfolio,

            market=market,

        )





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


            stats=get_summary_cards(),


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

            "Dashboard ready | Action=%s | AI=%d",

            decision.action,

            decision.ai_score,

        )





        return dashboard





    except DashboardError:

        raise





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