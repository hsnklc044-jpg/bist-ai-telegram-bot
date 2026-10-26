"""
QuantBIST
Exceptions.
"""

from __future__ import annotations


class FrameworkError(Exception):
    """Base class for QuantBIST errors."""


class ConfigurationError(FrameworkError):
    """Missing or invalid settings (.env)."""


class MarketError(FrameworkError):
    """Price data missing, too short or unusable."""


__all__ = [
    "FrameworkError",
    "ConfigurationError",
    "MarketError",
]
