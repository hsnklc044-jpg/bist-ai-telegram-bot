"""
QuantBIST RC4
Dashboard Charts
"""

from __future__ import annotations


def get_dashboard_charts() -> dict:
    """
    Dashboard grafik bilgilerini döndürür.
    """

    return {

        "equity_curve": {

            "title": "Equity Curve",

            "image": "/static/equity_curve.png",

        },

        "portfolio": {

            "title": "Portfolio Allocation",

            "image": "/static/portfolio_pie.png",

        },

    }