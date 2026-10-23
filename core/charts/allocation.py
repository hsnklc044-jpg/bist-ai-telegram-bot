"""
QuantBIST Framework
Portfolio Allocation Chart
"""

from __future__ import annotations

import plotly.express as px

from core.charts.base import (
    apply_layout,
    to_html,
)
from core.infrastructure.logger import (
    get_logger,
)
from core.portfolio.repository import (
    load_portfolio,
)

logger = get_logger(__name__)


# =====================================================
# HELPERS
# =====================================================

def _load_portfolio():
    """
    Load portfolio dataframe.
    """

    return load_portfolio()


# =====================================================
# PUBLIC API
# =====================================================

def generate_allocation_chart() -> str:
    """
    Generate interactive portfolio allocation chart.
    """

    logger.info(
        "Generating allocation chart."
    )

    portfolio = _load_portfolio()

    if portfolio.empty:

        logger.warning(
            "Portfolio is empty."
        )

        return ""

    fig = px.pie(

        portfolio,

        values="value",

        names="symbol",

        hole=0.45,

    )

    fig.update_traces(

        textposition="inside",

        textinfo="percent+label",

        hovertemplate=(
            "<b>%{label}</b>"
            "<br>"
            "Value: %{value:,.2f} TL"
            "<br>"
            "Weight: %{percent}"
            "<extra></extra>"
        ),

    )

    apply_layout(fig)

    fig.update_layout(

        title="Portfolio Allocation",

        showlegend=True,

        legend=dict(

            orientation="h",

            y=-0.15,

        ),

    )

    return to_html(fig)


# =====================================================
# EXPORTS
# =====================================================

__all__ = [

    "generate_allocation_chart",

]
