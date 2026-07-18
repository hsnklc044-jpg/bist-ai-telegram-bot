"""
QuantBIST Framework
Portfolio Models
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
    Final optimizer action.
    """

    BUY = "BUY"
    HOLD = "HOLD"
    REBALANCE = "REBALANCE"
    REDUCE_RISK = "REDUCE_RISK"


# =====================================================
# PORTFOLIO POSITION
# =====================================================

@dataclass(slots=True)
class Position:
    """
    Portfolio position.
    """

    symbol: str

    price: float

    quantity: float

    value: float

    weight: float = 0.0


# =====================================================
# DASHBOARD STATS
# =====================================================

@dataclass(slots=True)
class PortfolioStats:
    """
    Dashboard summary statistics.
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
    Portfolio health analysis.
    """

    score: float

    grade: str

    diversification: float

    concentration: float

    cash_ratio: float

    summary: str


# =====================================================
# RISK
# =====================================================

@dataclass(slots=True)
class PortfolioRisk:
    """
    Portfolio risk profile.
    """

    level: str

    score: float

    volatility: float

    max_drawdown: float

    sharpe: float

    summary: str


# =====================================================
# OPTIMIZATION
# =====================================================

@dataclass(slots=True)
class PortfolioOptimization:
    """
    Portfolio optimization result.

    Shared by:

    - Dashboard
    - Decision Engine
    - Recommendation Engine
    - Morning Report
    - Telegram Bot
    """

    # Portfolio Summary

    total_value: float

    # Largest Position

    largest_position: str

    largest_weight: float

    # Smallest Position

    smallest_position: str

    smallest_weight: float

    # Risk

    concentration_risk: bool

    rebalance: bool

    # Overall Quality

    health_score: int

    severity: PortfolioSeverity

    # Final Recommendation

    overall_action: PortfolioAction

    # Suggestions

    suggestions: list[str] = field(
        default_factory=list
    )


# =====================================================
# REBALANCER
# =====================================================

@dataclass(slots=True)
class RebalanceResult:
    """
    Portfolio rebalance analysis.
    """

    needs_rebalance: bool

    summary: str

    buy: list[str] = field(
        default_factory=list
    )

    sell: list[str] = field(
        default_factory=list
    )


# =====================================================
# ANALYZER
# =====================================================

@dataclass(slots=True)
class PortfolioAnalysis:
    """
    Final Portfolio Engine output.
    """

    stats: PortfolioStats

    health: PortfolioHealth

    risk: PortfolioRisk

    optimization: PortfolioOptimization

    rebalance: RebalanceResult