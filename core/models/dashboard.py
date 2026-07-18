"""
QuantBIST Framework
Dashboard View Model
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class DashboardModel:
    """
    Dashboard View Model.
    """

    stats: dict = field(default_factory=dict)

    portfolio: object | None = None

    market: object | None = None

    committee: object | None = None

    decision: object | None = None

    charts: dict = field(default_factory=dict)

    signals: list = field(default_factory=list)

    watchlist: list = field(default_factory=list)

    updated: str = ""


__all__ = [
    "DashboardModel",
]