"""
QuantBIST RC4
Dashboard Cards
"""

from core.dashboard.service import get_dashboard


def get_summary_card():

    dashboard = get_dashboard()

    return dashboard["stats"]


def get_top_signals_card():

    dashboard = get_dashboard()

    return dashboard["signals"]