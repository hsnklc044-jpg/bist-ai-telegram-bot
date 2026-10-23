"""
QuantBIST RC7
API Export Service

Export API facade.
"""

from __future__ import annotations

from core.config.paths import REPORTS_DIR
from core.export.service import (
    export_file as _export_file,
)
from core.export.service import (
    export_report as _export_report,
)
from core.export.service import (
    save_report as _save_report,
)
from core.models.dashboard import DashboardModel

# =====================================================
# PUBLIC API
# =====================================================

def export_report(
    dashboard: DashboardModel,
    format: str = "txt",
) -> str:
    """
    Export report as string.
    """
    return _export_report(
        dashboard,
        format=format,
    )


def save_report(
    dashboard: DashboardModel,
    path: str,
    format: str = "txt",
) -> str:
    """
    Save report to the given path.
    """
    return _save_report(
        dashboard,
        path=path,
        format=format,
    )


def export_file(
    dashboard: DashboardModel,
    format: str = "txt",
    directory: str = str(REPORTS_DIR),
) -> str:
    """
    Export report to a timestamped file.
    """
    return _export_file(
        dashboard,
        format=format,
        directory=directory,
    )


# =====================================================
# EXPORTS
# =====================================================

__all__ = [
    "export_report",
    "save_report",
    "export_file",
]
