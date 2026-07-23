"""
QuantBIST RC7
Markdown Export

Markdown report generator.
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


def export_markdown(
    dashboard: DashboardModel,
) -> str:
    """
    Export complete report as Markdown.
    """



    if dashboard is None:

        raise ValueError(
            "Dashboard cannot be empty."
        )





    report = generate_report(
        dashboard,
    )





    lines: list[str] = []



    lines.append(
        "# QUANTBIST RC7 REPORT"
    )


    lines.append("")



    lines.append(
        "---"
    )


    lines.append("")





    for section, content in report.items():



        lines.append(
            f"## {section.upper()}"
        )


        lines.append("")



        if isinstance(
            content,
            str,
        ):

            lines.append(
                content
            )


        else:

            lines.append(
                "```json"
            )


            lines.append(

                json.dumps(

                    content,

                    indent=4,

                    ensure_ascii=False,

                    default=str,

                )

            )


            lines.append(
                "```"
            )



        lines.append("")



        lines.append(
            "---"
        )


        lines.append("")





    return "\n".join(
        lines
    )





# =====================================================
# EXPORTS
# =====================================================


__all__ = [

    "export_markdown",

]
