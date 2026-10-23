"""
QuantBIST RC5
Chart Intelligence Service
"""

from __future__ import annotations

from core.charts.ai import (
    generate_ai_gauge,
)
from core.charts.allocation import (
    generate_allocation_chart,
)
from core.charts.equity import (
    generate_equity_chart,
)
from core.charts.risk import (
    generate_risk_gauge,
)
from core.infrastructure.logger import (
    get_logger,
)

logger = get_logger(__name__)





# =====================================================
# CHART HELPERS
# =====================================================


def get_portfolio_chart() -> str:
    """
    Portfolio allocation visualization.
    """

    try:

        return generate_allocation_chart()


    except Exception:


        logger.exception(

            "Portfolio chart generation failed."

        )


        return ""





def get_equity_chart() -> str:
    """
    Equity curve visualization.
    """

    try:

        return generate_equity_chart()


    except Exception:


        logger.exception(

            "Equity chart generation failed."

        )


        return ""





def get_risk_chart(
    score: float,
) -> str:
    """
    Risk gauge visualization.
    """

    try:

        return generate_risk_gauge(

            score,

        )


    except Exception:


        logger.exception(

            "Risk chart generation failed."

        )


        return ""





def get_ai_chart(
    score: float,
) -> str:
    """
    AI score visualization.
    """

    try:

        return generate_ai_gauge(

            score,

        )


    except Exception:


        logger.exception(

            "AI chart generation failed."

        )


        return ""





# =====================================================
# DASHBOARD BUILDER
# =====================================================


def get_dashboard_charts(
    *,
    risk_score: float = 0.0,
    ai_score: float = 0.0,
) -> dict[str, str]:
    """
    Generate complete dashboard chart package.

    Returns:

    {
        allocation,
        equity,
        risk,
        ai
    }

    """


    logger.info(

        "Dashboard charts generation started."

    )



    charts = {


        "allocation":

            get_portfolio_chart(),



        "equity":

            get_equity_chart(),



        "risk":

            get_risk_chart(

                risk_score,

            ),



        "ai":

            get_ai_chart(

                ai_score,

            ),

    }



    logger.info(

        "Dashboard charts completed."

    )


    return charts





__all__ = [

    "get_dashboard_charts",

    "get_portfolio_chart",

    "get_equity_chart",

    "get_risk_chart",

    "get_ai_chart",

]
