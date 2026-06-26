"""
QuantBIST RC4
Portfolio Domain Models
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PortfolioStats:
    """
    Portfolio summary statistics.
    """

    portfolio: float
    cash: float
    positions: int
    top_stock: str
    sharpe: float
    win_rate: float
    profit_factor: float
    max_drawdown: float