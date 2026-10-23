"""
QuantBIST RC5
Portfolio Domain Models
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

# =====================================================
# ENUMS
# =====================================================


class PortfolioSeverity(Enum):
    """
    Portfolio optimization severity.
    """

    LOW = "LOW"

    MEDIUM = "MEDIUM"

    HIGH = "HIGH"

    CRITICAL = "CRITICAL"





class PortfolioAction(Enum):
    """
    Portfolio recommended action.
    """

    BUY = "BUY"

    HOLD = "HOLD"

    REBALANCE = "REBALANCE"

    REDUCE_RISK = "REDUCE_RISK"







# =====================================================
# POSITION
# =====================================================


@dataclass(slots=True)
class Position:
    """
    Single portfolio position.
    """

    symbol: str

    price: float

    quantity: float

    value: float

    weight: float = 0.0







# =====================================================
# PORTFOLIO STATS
# =====================================================


@dataclass(slots=True)
class PortfolioStats:
    """
    Dashboard portfolio statistics.
    """

    portfolio: float

    cash: float

    positions: int

    top_stock: str


    sharpe: float

    win_rate: float

    profit_factor: float

    max_drawdown: float







# =====================================================
# HEALTH
# =====================================================


@dataclass(slots=True)
class PortfolioHealth:
    """
    Portfolio health intelligence.
    """

    score: float

    grade: str

    diversification: float

    concentration: float

    cash_ratio: float

    summary: str



    @property
    def healthy(
        self,
    ) -> bool:

        return self.score >= 80







# =====================================================
# RISK
# =====================================================


@dataclass(slots=True)
class PortfolioRisk:
    """
    Portfolio risk intelligence.
    """

    level: str

    score: float

    volatility: float

    max_drawdown: float

    sharpe: float

    summary: str



    @property
    def high_risk(
        self,
    ) -> bool:

        return self.level.upper() in (

            "HIGH",

            "CRITICAL",

        )







# =====================================================
# OPTIMIZATION
# =====================================================


@dataclass(slots=True)
class PortfolioOptimization:
    """
    Portfolio optimization result.
    """


    total_value: float


    largest_position: str

    largest_weight: float


    smallest_position: str

    smallest_weight: float



    best_symbol: str = "-"

    worst_symbol: str = "-"



    concentration_risk: bool = False


    rebalance: bool = False



    health_score: int = 100



    severity: PortfolioSeverity = PortfolioSeverity.LOW



    overall_action: PortfolioAction = PortfolioAction.HOLD



    suggestions: list[str] = field(

        default_factory=list,

    )







# =====================================================
# REBALANCE
# =====================================================


@dataclass(slots=True)
class RebalanceResult:
    """
    Portfolio rebalance plan.
    """


    needs_rebalance: bool


    summary: str



    buy: list[str] = field(

        default_factory=list,

    )


    sell: list[str] = field(

        default_factory=list,

    )







# =====================================================
# FINAL ANALYSIS
# =====================================================


@dataclass(slots=True)
class PortfolioAnalysis:
    """
    Complete RC5 portfolio intelligence output.
    """


    stats: PortfolioStats


    health: PortfolioHealth


    risk: PortfolioRisk


    optimization: PortfolioOptimization


    rebalance: RebalanceResult






    @property
    def health_score(
        self,
    ) -> float:

        return self.health.score






    @property
    def risk_level(
        self,
    ) -> str:

        return self.risk.level






    @property
    def needs_rebalance(
        self,
    ) -> bool:

        return self.rebalance.needs_rebalance






    @property
    def concentration_risk(
        self,
    ) -> bool:

        return self.optimization.concentration_risk






    @property
    def investable(
        self,
    ) -> bool:

        return (

            self.health.score >= 70

            and

            self.risk.level.upper()
            not in (

                "HIGH",

                "CRITICAL",

            )

        )







# =====================================================
# EXPORTS
# =====================================================


__all__ = [

    "PortfolioSeverity",

    "PortfolioAction",

    "Position",

    "PortfolioStats",

    "PortfolioHealth",

    "PortfolioRisk",

    "PortfolioOptimization",

    "RebalanceResult",

    "PortfolioAnalysis",

]
