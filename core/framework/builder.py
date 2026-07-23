"""
QuantBIST Framework
Framework Builder
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.framework.plugin import (
    plugin_manager,
)

from core.framework.registry import (
    registry,
)

from core.infrastructure.logger import (
    get_logger,
)

logger = get_logger(__name__)


# =====================================================
# MODEL
# =====================================================

@dataclass(slots=True)
class Framework:
    """
    QuantBIST Framework container.
    """

    registry: Any

    plugins: Any


# =====================================================
# HELPERS
# =====================================================

def register_default_services() -> None:
    """
    Register built-in framework services.
    """

    from core.charts.service import (
        get_dashboard_charts,
    )

    from core.committee.service import (
        get_committee_report,
    )

    from core.decision.service import (
        get_decision,
    )

    from core.market.service import (
        get_market_status,
    )

    from core.portfolio.service import (
        get_portfolio_report,
    )

    services = {

        "portfolio": get_portfolio_report,

        "market": get_market_status,

        "committee": get_committee_report,

        "decision": get_decision,

        "charts": get_dashboard_charts,

    }

    for name, service in services.items():

        if not registry.exists(name):

            registry.register(

                name,

                service,

            )


def initialize_plugins() -> None:
    """
    Initialize all enabled plugins.
    """

    plugin_manager.initialize_all()


# =====================================================
# PUBLIC API
# =====================================================

def build_framework() -> Framework:
    """
    Build QuantBIST Framework.
    """

    logger.info(
        "Building framework..."
    )

    register_default_services()

    initialize_plugins()

    framework = Framework(

        registry=registry,

        plugins=plugin_manager,

    )

    logger.info(
        "Framework ready."
    )

    return framework


# =====================================================
# EXPORTS
# =====================================================

__all__ = [

    "Framework",

    "build_framework",

]
