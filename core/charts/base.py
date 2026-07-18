"""
QuantBIST Framework
Base Plotly Configuration
"""

from __future__ import annotations

import plotly.graph_objects as go


DEFAULT_LAYOUT = {

    "template": "plotly_dark",

    "paper_bgcolor": "#0f172a",

    "plot_bgcolor": "#0f172a",

    "font": {

        "color": "white",

        "family": "Segoe UI",

        "size": 13,

    },

    "margin": {

        "l": 20,

        "r": 20,

        "t": 45,

        "b": 20,

    },

    "legend": {

        "orientation": "h",

        "y": -0.15,

    },

}


def apply_layout(

    figure: go.Figure,

) -> go.Figure:
    """
    Apply QuantBIST layout.
    """

    figure.update_layout(

        **DEFAULT_LAYOUT

    )

    return figure


def to_html(

    figure: go.Figure,

) -> str:
    """
    Convert figure to embeddable HTML.
    """

    return figure.to_html(

        include_plotlyjs="cdn",

        full_html=False,

    )