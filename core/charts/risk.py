"""
QuantBIST Framework
Risk Gauge Chart
"""

from __future__ import annotations

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
# HELPERS
# =====================================================

def _risk_color(
    score: float,
) -> str:
    """
    Select gauge color.
    """

    if score <= 20:
        return "#22c55e"

    if score <= 40:
        return "#84cc16"

    if score <= 60:
        return "#facc15"

    if score <= 80:
        return "#fb923c"

    return "#ef4444"


# =====================================================
# PUBLIC API
# =====================================================

def generate_risk_gauge(
    score: float,
) -> str:
    """
    Generate interactive risk gauge.

    Parameters
    ----------
    score
        Risk score (0-100)

    Returns
    -------
    str
        Plotly HTML
    """

    logger.info(
        "Generating risk gauge."
    )

    score = max(
        0.0,
        min(
            float(score),
            100.0,
        ),
    )

    fig = go.Figure(

        go.Indicator(

            mode="gauge+number",

            value=score,

            number={

                "suffix": "%",

                "font": {

                    "size": 42,

                },

            },

            title={

                "text": "Portfolio Risk",

                "font": {

                    "size": 22,

                },

            },

            gauge={

                "axis": {

                    "range": [

                        0,

                        100,

                    ],

                },

                "bar": {

                    "color": _risk_color(
                        score,
                    ),

                    "thickness": 0.35,

                },

                "steps": [

                    {

                        "range": [

                            0,

                            20,

                        ],

                        "color": "#14532d",

                    },

                    {

                        "range": [

                            20,

                            40,

                        ],

                        "color": "#3f6212",

                    },

                    {

                        "range": [

                            40,

                            60,

                        ],

                        "color": "#854d0e",

                    },

                    {

                        "range": [

                            60,

                            80,

                        ],

                        "color": "#9a3412",

                    },

                    {

                        "range": [

                            80,

                            100,

                        ],

                        "color": "#7f1d1d",

                    },

                ],

                "threshold": {

                    "line": {

                        "color": "white",

                        "width": 4,

                    },

                    "thickness": 0.8,

                    "value": score,

                },

            },

        )

    )

    apply_layout(
        fig,
    )

    fig.update_layout(

        height=320,

        margin=dict(

            l=20,

            r=20,

            t=60,

            b=20,

        ),

    )

    return to_html(
        fig,
    )


# =====================================================
# EXPORTS
# =====================================================

__all__ = [

    "generate_risk_gauge",

]