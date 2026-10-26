"""
QuantBIST
Trading assumptions shared by the backtest, the paper account and reports.
"""

from __future__ import annotations

COMMISSION = 0.001  # per side, share of traded value
SLIPPAGE = 0.0005  # per side, applied to the fill price
PAPER_INITIAL_CAPITAL = 100_000.0  # TL, starting cash of the paper account

ACCOUNTS = ("real", "paper")

__all__ = ["COMMISSION", "SLIPPAGE", "PAPER_INITIAL_CAPITAL", "ACCOUNTS"]
