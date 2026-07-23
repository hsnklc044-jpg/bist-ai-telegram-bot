"""
QuantBIST RC7
API Service

Central access point for all QuantBIST services.
"""

from __future__ import annotations

from core.models.dashboard import DashboardModel
from core.decision.models import Decision

from .dashboard import get_dashboard
from .decision import get_decision
from .reports import get_report
from .export import (
    export_report,
    save_report,
    export_file,
)


# =====================================================
# DASHBOARD
# =====================================================

def dashboard() -> DashboardModel:
    """
    Return complete dashboard.
    """
    return get_dashboard()


# =====================================================
# DECISION
# =====================================================

def decision(
    *args,
    **kwargs,
) -> Decision:
    """
    Return latest investment decision.
    """
    return get_decision(
        *args,
        **kwargs,
    )


# =====================================================
# REPORTS
# =====================================================

def report(
    dashboard: DashboardModel,
) -> dict:
    """
    Generate report package.
    """
    return get_report(
        dashboard,
    )


# =====================================================
# EXPORTS
# =====================================================

__all__ = [
    "dashboard",
    "decision",
    "report",
    "export_report",
    "save_report",
    "export_file",
]
