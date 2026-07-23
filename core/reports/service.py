"""
QuantBIST RC7
Reports Service

Single entry point
for all report generation.
"""

from __future__ import annotations


from core.models.dashboard import (
    DashboardModel,
)


from core.reports.summary import (
    generate_summary_report,
)


from core.reports.portfolio import (
    generate_portfolio_report,
)


from core.reports.market import (
    generate_market_report,
)


from core.reports.decision import (
    generate_decision_report,
)





# =====================================================
# PUBLIC API
# =====================================================


def generate_report(
    dashboard: DashboardModel,
) -> dict:
    """
    Generate complete QuantBIST report package.

    RC7 Flow

        DashboardModel
              │
              ▼
        Reports Service
              │
              ├── Summary
              ├── Portfolio
              ├── Market
              └── Decision

    No duplicate calculations.
    """



    if dashboard is None:

        raise ValueError(

            "Dashboard cannot be empty."

        )





    return {

        "summary":

            generate_summary_report(

                dashboard,

            ),


        "portfolio":

            generate_portfolio_report(

                dashboard,

            ),


        "market":

            generate_market_report(

                dashboard,

            ),


        "decision":

            generate_decision_report(

                dashboard.decision,

            ),

    }






# =====================================================
# SHORTCUTS
# =====================================================


def generate_summary(
    dashboard: DashboardModel,
) -> str:
    """
    Generate summary report.
    """

    return generate_summary_report(

        dashboard,

    )





def generate_portfolio(
    dashboard: DashboardModel,
) -> str:
    """
    Generate portfolio report.
    """

    return generate_portfolio_report(

        dashboard,

    )





def generate_market(
    dashboard: DashboardModel,
) -> str:
    """
    Generate market report.
    """

    return generate_market_report(

        dashboard,

    )





def generate_decision(
    dashboard: DashboardModel,
) -> str:
    """
    Generate decision report.
    """

    return generate_decision_report(

        dashboard.decision,

    )





# =====================================================
# EXPORTS
# =====================================================


__all__ = [

    "generate_report",

    "generate_summary",

    "generate_portfolio",

    "generate_market",

    "generate_decision",

]
