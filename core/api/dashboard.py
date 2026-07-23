"""
QuantBIST RC6
API Dashboard Service

Dashboard API facade.
"""

from __future__ import annotations


from core.dashboard.service import (
    get_dashboard as _get_dashboard,
)


from core.models.dashboard import (
    DashboardModel,
)





# =====================================================
# PUBLIC API
# =====================================================


def get_dashboard() -> DashboardModel:
    """
    Return complete dashboard intelligence.

    Source:

        core.dashboard.service

    Flow:

        Portfolio
            |
        Market
            |
        Decision
            |
        Dashboard

    """


    return _get_dashboard()





# =====================================================
# EXPORTS
# =====================================================


__all__ = [

    "get_dashboard",

]