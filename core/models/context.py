"""
QuantBIST Framework
Dashboard Context Model
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Any


@dataclass(slots=True)
class DashboardContext:
    """
    Shared application context.

    This model is passed between services,
    charts, templates and reporting engines.
    """

    # -------------------------------------------------
    # Core Services
    # -------------------------------------------------

    portfolio: Any | None = None

    market: Any | None = None

    committee: Any | None = None

    decision: Any | None = None

    # -------------------------------------------------
    # Dashboard Cards
    # -------------------------------------------------

    stats: dict = field(default_factory=dict)

    signals: list = field(default_factory=list)

    watchlist: list = field(default_factory=list)

    # -------------------------------------------------
    # Charts
    # -------------------------------------------------

    charts: dict = field(default_factory=dict)

    # -------------------------------------------------
    # AI Scores
    # -------------------------------------------------

    risk_score: float = 0.0

    ai_score: float = 0.0

    market_score: float = 0.0

    portfolio_score: float = 0.0

    # -------------------------------------------------
    # Metadata
    # -------------------------------------------------

    updated: str = ""

    version: str = "RC4"

    environment: str = "Development"

    # -------------------------------------------------
    # Helpers
    # -------------------------------------------------

    @property
    def healthy(self) -> bool:
        """
        Overall system healthy?
        """

        return (

            self.ai_score >= 60

            and

            self.risk_score <= 40

        )

    @property
    def risk_on(self) -> bool:
        """
        Risk-on environment.
        """

        return self.market_score >= 60

    @property
    def risk_off(self) -> bool:
        """
        Risk-off environment.
        """

        return not self.risk_on

    @property
    def dashboard_score(self) -> float:
        """
        Composite dashboard score.
        """

        scores = [

            self.ai_score,

            100 - self.risk_score,

            self.market_score,

            self.portfolio_score,

        ]

        return round(

            sum(scores) / len(scores),

            2,

        )


__all__ = [

    "DashboardContext",

]
