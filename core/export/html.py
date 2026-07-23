"""
QuantBIST RC6
HTML Export

HTML report generator.
"""

from __future__ import annotations


import html
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


def export_html(
    dashboard: DashboardModel,
) -> str:
    """
    Export complete report as HTML.
    """



    if dashboard is None:

        raise ValueError(
            "Dashboard cannot be empty."
        )





    report = generate_report(
        dashboard,
    )





    sections: list[str] = []





    for name, content in report.items():


        if isinstance(
            content,
            str,
        ):

            body = html.escape(
                content
            )


        else:

            body = html.escape(

                json.dumps(

                    content,

                    indent=4,

                    ensure_ascii=False,

                    default=str,

                )

            )





        sections.append(

            f"""
            <section>

                <h2>{name.upper()}</h2>

                <pre>{body}</pre>

            </section>
            """

        )





    return f"""
<!DOCTYPE html>

<html lang="tr">

<head>

<meta charset="UTF-8">

<title>
QuantBIST RC6 Report
</title>


<style>

body {{

    font-family:
    Arial,
    sans-serif;

    margin: 40px;

    background:
    #f5f5f5;

}}


h1 {{

    text-align:center;

}}


section {{

    background:white;

    padding:20px;

    margin-bottom:20px;

    border-radius:10px;

}}


h2 {{

    border-bottom:
    1px solid #ddd;

    padding-bottom:10px;

}}


pre {{

    white-space:
    pre-wrap;

    font-size:
    14px;

}}


</style>


</head>


<body>


<h1>
QUANTBIST RC6 REPORT
</h1>


{''.join(sections)}


</body>


</html>
"""





# =====================================================
# EXPORTS
# =====================================================


__all__ = [

    "export_html",

]