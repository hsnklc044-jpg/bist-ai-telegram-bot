"""
QuantBIST Framework
Framework Service
"""

from __future__ import annotations

from core.dashboard.builder import (
    build_dashboard,
)

from core.dashboard.context import (
    build_dashboard_context,
)

from core.models.context import (
    DashboardContext,
)

from core.models.dashboard import (
    DashboardModel,
)


class FrameworkService:
    """
    QuantBIST Application Framework.
    """

    def build_context(
        self,
    ) -> DashboardContext:

        return build_dashboard_context()

    def build_dashboard(
        self,
    ) -> DashboardModel:

        context = self.build_context()

        return build_dashboard(
            context,
        )


framework = FrameworkService()


__all__ = [

    "FrameworkService",

    "framework",

]
