"""
QuantBIST RC6
TXT Export
"""

from __future__ import annotations

import json

from core.models.dashboard import DashboardModel
from core.reports.service import generate_report


# =====================================================
# PUBLIC API
# =====================================================

def export_txt(
    dashboard: DashboardModel,
) -> str:
    """
    Export complete report as plain text.
    """

    report = generate_report(dashboard)

    lines: list[str] = []

    lines.append("=" * 80)
    lines.append("QUANTBIST RC6 REPORT")
    lines.append("=" * 80)
    lines.append("")

    for section, content in report.items():

        lines.append("=" * 80)
        lines.append(section.upper())
        lines.append("=" * 80)

        if isinstance(content, str):

            lines.append(content)

        else:

            lines.append(
                json.dumps(
                    content,
                    indent=4,
                    ensure_ascii=False,
                    default=str,
                )
            )

        lines.append("")

    return "\n".join(lines)


# =====================================================
# EXPORTS
# =====================================================

__all__ = [

    "export_txt",

]