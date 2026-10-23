"""
QuantBIST RC7
Export Service

Central export entry point.

Dashboard
    ↓
Reports
    ↓
Export
    ↓
File Output
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from core.export.html import (
    export_html,
)
from core.export.json import (
    export_json,
)
from core.export.markdown import (
    export_markdown,
)
from core.export.txt import (
    export_txt,
)
from core.models.dashboard import (
    DashboardModel,
)

# =====================================================
# FORMAT CONSTANTS
# =====================================================


TXT = "txt"

MARKDOWN = "markdown"

HTML = "html"

JSON = "json"





# =====================================================
# EXPORT ENGINE
# =====================================================


def export_report(
    dashboard: DashboardModel,
    format: str = TXT,
) -> str:
    """
    Generate report output.

    Supported:

        txt
        markdown
        html
        json

    """


    if dashboard is None:

        raise ValueError(

            "Dashboard cannot be empty."

        )



    format = format.lower()



    if format == TXT:

        return export_txt(

            dashboard,

        )



    if format == MARKDOWN:

        return export_markdown(

            dashboard,

        )



    if format == HTML:

        return export_html(

            dashboard,

        )



    if format == JSON:

        return export_json(

            dashboard,

        )



    raise ValueError(

        f"Unsupported export format: {format}"

    )







# =====================================================
# SAVE ENGINE
# =====================================================


def save_report(
    dashboard: DashboardModel,
    path: str,
    format: str = TXT,
) -> str:
    """
    Generate and save report file.

    Example:

        save_report(
            dashboard,
            "reports/output/report.html",
            "html"
        )

    """


    content = export_report(

        dashboard,

        format,

    )



    file_path = Path(

        path

    )



    file_path.parent.mkdir(

        parents=True,

        exist_ok=True,

    )



    file_path.write_text(

        content,

        encoding="utf-8",

    )



    return str(

        file_path

    )







# =====================================================
# AUTO FILE EXPORT
# =====================================================


def export_file(
    dashboard: DashboardModel,
    format: str = HTML,
    directory: str = "reports/output",
) -> str:
    """
    Generate automatic report file.

    Example:

        export_file(
            dashboard,
            "html"
        )

    Creates:

        reports/output/
        quantbist_report_DATE.html

    """


    format = format.lower()



    extension_map = {

        TXT:
            "txt",


        MARKDOWN:
            "md",


        HTML:
            "html",


        JSON:
            "json",

    }



    if format not in extension_map:

        raise ValueError(

            f"Unsupported export format: {format}"

        )



    timestamp = datetime.now().strftime(

        "%Y%m%d_%H%M%S"

    )



    filename = (

        "quantbist_report_"

        f"{timestamp}."

        f"{extension_map[format]}"

    )



    path = Path(

        directory

    ) / filename



    return save_report(

        dashboard,

        str(path),

        format,

    )







# =====================================================
# SHORTCUTS
# =====================================================


def export_as_txt(
    dashboard: DashboardModel,
) -> str:


    return export_txt(

        dashboard,

    )





def export_as_markdown(
    dashboard: DashboardModel,
) -> str:


    return export_markdown(

        dashboard,

    )





def export_as_html(
    dashboard: DashboardModel,
) -> str:


    return export_html(

        dashboard,

    )





def export_as_json(
    dashboard: DashboardModel,
) -> str:


    return export_json(

        dashboard,

    )





# =====================================================
# EXPORTS
# =====================================================


__all__ = [

    "export_report",

    "save_report",

    "export_file",

    "export_as_txt",

    "export_as_markdown",

    "export_as_html",

    "export_as_json",

]
