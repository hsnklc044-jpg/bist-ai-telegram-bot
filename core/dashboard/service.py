"""
QuantBIST Framework
Dashboard Service
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
    Build complete dashboard model.
    """

    logger.info(
        "Preparing dashboard..."
    )

    try:

        # ---------------------------------------------
        # Portfolio
        # ---------------------------------------------

        portfolio_stats = get_dashboard_stats()

        portfolio = get_portfolio_analysis(
            portfolio_stats,
        )


        # ---------------------------------------------
        # Market
        # ---------------------------------------------

        market = get_market_status()


        # ---------------------------------------------
        # Investment Committee
        # ---------------------------------------------

        committee = get_committee_decision(

            portfolio,

            market,

        )


        # ---------------------------------------------
        # Scores
        # ---------------------------------------------

        risk_score = 0.0

        try:

            risk_score = float(
                portfolio.risk.score
            )

        except Exception:

            logger.warning(
                "Portfolio risk score unavailable."
            )


        ai_score = 0.0

        try:

            ai_score = float(
                committee.confidence
            )

        except Exception:

            logger.warning(
                "Committee confidence unavailable."
            )


        # ---------------------------------------------
        # Charts
        # ---------------------------------------------

        charts = get_dashboard_charts(

            risk_score=risk_score,

            ai_score=ai_score,

        )


        # ---------------------------------------------
        # Dashboard Model
        # ---------------------------------------------

        dashboard = DashboardModel(

            stats=get_summary_cards(),

            portfolio=portfolio,

            market=market,

            committee=committee,

            charts=charts,

            signals=get_signals_card(),

            watchlist=get_watchlist_card(),

            # Önemli:
            # datetime nesnesi gönderiyoruz.
            # Formatlama Jinja2 template tarafında yapılacak.

            updated=datetime.now(),

        )


        logger.info(
            "Dashboard ready."
        )


        return dashboard


    except Exception:

        logger.exception(
            "Dashboard generation failed."
        )

        raise



# =====================================================
# EXPORTS
# =====================================================

__all__ = [

    "get_dashboard",

]