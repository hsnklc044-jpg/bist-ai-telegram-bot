"""
QuantBIST Framework
Chart Service
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
# INDIVIDUAL CHARTS
# =====================================================

def get_portfolio_chart() -> str:
    """
    Portfolio allocation chart.
    """

    try:

        return generate_allocation_chart()

    except Exception:

        logger.exception(
            "Portfolio allocation chart failed."
        )

        return ""


def get_equity_chart() -> str:
    """
    Equity curve chart.
    """

    try:

        return generate_equity_chart()

    except Exception:

        logger.exception(
            "Equity chart failed."
        )

        return ""


def get_risk_chart(
    score: float,
) -> str:
    """
    Portfolio risk gauge.
    """

    try:

        return generate_risk_gauge(
            score,
        )

    except Exception:

        logger.exception(
            "Risk gauge failed."
        )

        return ""


def get_ai_chart(
    score: float,
) -> str:
    """
    AI confidence gauge.
    """

    try:

        return generate_ai_gauge(
            score,
        )

    except Exception:

        logger.exception(
            "AI gauge failed."
        )

        return ""


# =====================================================
# DASHBOARD
# =====================================================

def get_dashboard_charts(
    *,
    risk_score: float = 0.0,
    ai_score: float = 0.0,
) -> dict[str, str]:
    """
    Build dashboard charts.
    """

    logger.info(
        "Preparing dashboard charts."
    )

    charts = {

        "allocation": get_portfolio_chart(),

        "equity": get_equity_chart(),

        "risk": get_risk_chart(
            risk_score,
        ),

        "ai": get_ai_chart(
            ai_score,
        ),

    }

    logger.info(
        "Dashboard charts ready."
    )

    return charts


# =====================================================
# EXPORTS
# =====================================================

__all__ = [

    "get_dashboard_charts",

    "get_portfolio_chart",

    "get_equity_chart",

    "get_risk_chart",

    "get_ai_chart",

]