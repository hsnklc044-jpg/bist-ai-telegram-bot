"""
QuantBIST Framework
Equity Curve Chart
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from core.charts.base import (
    apply_layout,
    to_html,
)

from core.infrastructure.logger import (
    get_logger,
)

logger = get_logger(__name__)

# =====================================================
# CONFIG
# =====================================================

EQUITY_FILE = Path(
    "data/equity_curve.csv"
)

# =====================================================
# HELPERS
# =====================================================


def _load_equity() -> pd.DataFrame:
    """
    Load equity curve data.
    """

    if not EQUITY_FILE.exists():

        logger.warning(
            "Equity curve file not found."
        )

        return pd.DataFrame()

    df = pd.read_csv(EQUITY_FILE)

    df.columns = [

        str(column)
        .strip()
        .lower()

        for column in df.columns

    ]

    return df


# =====================================================
# PUBLIC API
# =====================================================


def generate_equity_chart() -> str:
    """
    Generate interactive equity curve.
    """

    logger.info(
        "Generating equity chart."
    )

    df = _load_equity()

    if df.empty:

        return ""

    if "trade" not in df.columns:

        return ""

    if "equity" not in df.columns:

        return ""

    fig = go.Figure()

    fig.add_trace(

        go.Scatter(

            x=df["trade"],

            y=df["equity"],

            mode="lines",

            name="Portfolio",

            line=dict(

                width=3,

            ),

        )

    )

    apply_layout(fig)

    fig.update_layout(

        title="Equity Curve",

        xaxis_title="Trade",

        yaxis_title="Portfolio Value",

        hovermode="x unified",

    )

    return to_html(fig)


# =====================================================
# EXPORTS
# =====================================================

__all__ = [

    "generate_equity_chart",

]