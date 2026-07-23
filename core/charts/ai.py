"""
QuantBIST Framework
AI Confidence Gauge
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

def _confidence_color(
    score: float,
) -> str:
    """
    Select gauge color.
    """

    if score >= 80:
        return "#22c55e"

    if score >= 60:
        return "#84cc16"

    if score >= 40:
        return "#facc15"

    if score >= 20:
        return "#fb923c"

    return "#ef4444"


def _confidence_label(
    score: float,
) -> str:
    """
    Convert score to label.
    """

    if score >= 80:
        return "VERY HIGH"

    if score >= 60:
        return "HIGH"

    if score >= 40:
        return "MEDIUM"

    if score >= 20:
        return "LOW"

    return "VERY LOW"


# =====================================================
# PUBLIC API
# =====================================================

def generate_ai_gauge(
    score: float,
) -> str:
    """
    Generate AI confidence gauge.

    Parameters
    ----------
    score
        AI confidence (0-100)

    Returns
    -------
    str
        Plotly HTML
    """

    logger.info(
        "Generating AI gauge."
    )

    score = max(
        0.0,
        min(
            float(score),
            100.0,
        ),
    )

    label = _confidence_label(
        score,
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

                "text": (
                    "AI Confidence"
                    "<br>"
                    f"<span style='font-size:15px'>"
                    f"{label}"
                    "</span>"
                ),

            },

            gauge={

                "axis": {

                    "range": [

                        0,

                        100,

                    ],

                    "tickwidth": 1,

                },

                "bar": {

                    "color": _confidence_color(
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

                        "color": "#7f1d1d",

                    },

                    {

                        "range": [

                            20,

                            40,

                        ],

                        "color": "#9a3412",

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

                        "color": "#3f6212",

                    },

                    {

                        "range": [

                            80,

                            100,

                        ],

                        "color": "#14532d",

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

    "generate_ai_gauge",

]
