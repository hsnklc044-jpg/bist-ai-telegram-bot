"""
QuantBIST Framework
Plugin Architecture
"""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod

from core.infrastructure.logger import (
    get_logger,
)

logger = get_logger(__name__)


class FrameworkPlugin(ABC):
    """
    Base class for all QuantBIST plugins.
    """

    name: str = "plugin"

    version: str = "1.0"

    enabled: bool = True

    @abstractmethod
    def initialize(
        self,
    ) -> None:
        """
        Initialize plugin.
        """

    @abstractmethod
    def execute(
        self,
        context,
    ):
        """
        Execute plugin.
        """

    def shutdown(
        self,
    ) -> None:
        """
        Shutdown plugin.
        """

        logger.info(
            "%s shutdown.",
            self.name,
        )


class PluginManager:
    """
    Manage framework plugins.
    """

    def __init__(
        self,
    ) -> None:

        self._plugins: dict[str, FrameworkPlugin] = {}

    # -------------------------------------------------
    # Register
    # -------------------------------------------------

    def register(
        self,
        plugin: FrameworkPlugin,
    ) -> None:

        self._plugins[
            plugin.name
        ] = plugin

        logger.info(
            "Plugin registered: %s",
            plugin.name,
        )

    # -------------------------------------------------
    # Initialize
    # -------------------------------------------------

    def initialize_all(
        self,
    ) -> None:

        for plugin in self._plugins.values():

            if plugin.enabled:

                plugin.initialize()

    # -------------------------------------------------
    # Execute
    # -------------------------------------------------

    def execute_all(
        self,
        context,
    ) -> dict:

        results = {}

        for plugin in self._plugins.values():

            if not plugin.enabled:

                continue

            try:

                results[
                    plugin.name
                ] = plugin.execute(
                    context,
                )

            except Exception:

                logger.exception(
                    "Plugin failed: %s",
                    plugin.name,
                )

        return results

    # -------------------------------------------------
    # Shutdown
    # -------------------------------------------------

    def shutdown_all(
        self,
    ) -> None:

        for plugin in self._plugins.values():

            plugin.shutdown()

    # -------------------------------------------------
    # Helpers
    # -------------------------------------------------

    def plugins(
        self,
    ) -> list[str]:

        return sorted(
            self._plugins.keys()
        )

    def count(
        self,
    ) -> int:

        return len(
            self._plugins
        )


plugin_manager = PluginManager()


__all__ = [

    "FrameworkPlugin",

    "PluginManager",

    "plugin_manager",

]
