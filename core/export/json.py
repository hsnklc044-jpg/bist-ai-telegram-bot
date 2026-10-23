"""
QuantBIST RC7
JSON Export

JSON report generator.
"""

from __future__ import annotations

import json

from core.models.dashboard import (
    DashboardModel,
)
from core.reports.service import (
    generate_report,
)

# =====================================================
# PUBLIC API
# =====================================================


def export_json(
    dashboard: DashboardModel,
) -> str:
    """
    Export complete report as JSON.
    """



    if dashboard is None:

        raise ValueError(
            "Dashboard cannot be empty."
        )





    report = generate_report(
        dashboard,
    )





    return json.dumps(

        report,

        indent=4,

        ensure_ascii=False,

        default=str,

    )





# =====================================================
# EXPORTS
# =====================================================


__all__ = [

    "export_json",

]
