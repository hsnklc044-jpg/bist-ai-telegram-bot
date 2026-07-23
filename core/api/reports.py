"""
QuantBIST RC6
API Reports Service

Reports API facade.
"""

from __future__ import annotations


from core.models.dashboard import (
    DashboardModel,
)


from core.reports.service import (
    generate_report as _generate_report,
)





# =====================================================
# PUBLIC API
# =====================================================


def get_report(
    dashboard: DashboardModel,
) -> dict:
    """
    Generate complete report package.

    Source:

        core.reports.service

    Includes:

        - Summary
        - Portfolio
        - Market
        - Decision

    """


    return _generate_report(

        dashboard,

    )





# =====================================================
# EXPORTS
# =====================================================


__all__ = [

    "get_report",

]