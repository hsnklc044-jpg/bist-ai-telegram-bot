"""
QuantBIST Framework
Service Registry
"""

from __future__ import annotations

from collections.abc import Callable

from core.infrastructure.logger import (
    get_logger,
)

logger = get_logger(__name__)


class ServiceRegistry:
    """
    Framework service registry.
    """

    def __init__(self) -> None:

        self._services: dict[str, Callable] = {}

    # -------------------------------------------------
    # Register
    # -------------------------------------------------

    def register(
        self,
        name: str,
        service: Callable,
    ) -> None:
        """
        Register service.
        """

        self._services[name] = service

        logger.info(
            "Registered service: %s",
            name,
        )

    # -------------------------------------------------
    # Resolve
    # -------------------------------------------------

    def get(
        self,
        name: str,
    ) -> Callable:
        """
        Resolve service.
        """

        if name not in self._services:

            raise KeyError(
                f"Service '{name}' not registered."
            )

        return self._services[name]

    # -------------------------------------------------
    # Exists
    # -------------------------------------------------

    def exists(
        self,
        name: str,
    ) -> bool:

        return name in self._services

    # -------------------------------------------------
    # Remove
    # -------------------------------------------------

    def unregister(
        self,
        name: str,
    ) -> None:

        self._services.pop(
            name,
            None,
        )

    # -------------------------------------------------
    # List
    # -------------------------------------------------

    def names(
        self,
    ) -> list[str]:

        return sorted(
            self._services.keys()
        )

    def services(
        self,
    ) -> dict[str, Callable]:

        return self._services.copy()

    # -------------------------------------------------
    # Magic
    # -------------------------------------------------

    def __contains__(
        self,
        name: str,
    ) -> bool:

        return self.exists(
            name,
        )

    def __len__(
        self,
    ) -> int:

        return len(
            self._services,
        )


registry = ServiceRegistry()


__all__ = [

    "ServiceRegistry",

    "registry",

]
