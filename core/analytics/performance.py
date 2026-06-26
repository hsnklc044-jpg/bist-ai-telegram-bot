"""
QuantBIST RC4
Performance Analytics
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


EQUITY_FILE = Path("data/equity_curve.csv")


def get_performance_stats() -> dict[str, float]:
    """
    Calculate portfolio performance metrics.
    """

    if not EQUITY_FILE.exists():
        return {
            "total_return": 0.0,
            "max_drawdown": 0.0,
            "sharpe": 0.0,
            "profit_factor": 0.0,
            "win_rate": 0.0,
        }

    df = pd.read_csv(EQUITY_FILE)

    if df.empty:
        return {
            "total_return": 0.0,
            "max_drawdown": 0.0,
            "sharpe": 0.0,
            "profit_factor": 0.0,
            "win_rate": 0.0,
        }

    equity = df["equity"]

    initial = float(equity.iloc[0])
    final = float(equity.iloc[-1])

    total_return = round(
        ((final - initial) / initial) * 100,
        2,
    )

    running_max = equity.cummax()

    drawdown = (
        (equity - running_max)
        / running_max
        * 100
    )

    max_drawdown = abs(
        round(drawdown.min(), 2)
    )

    returns = equity.pct_change().dropna()

    sharpe = 0.0

    if len(returns) > 1 and returns.std() != 0:
        sharpe = round(
            (
                returns.mean()
                / returns.std()
            )
            * (252 ** 0.5),
            2,
        )

    profit_factor = round(
        final / initial,
        2,
    )

    win_rate = 0.0

    if len(returns) > 0:
        win_rate = round(
            (
                (returns > 0).sum()
                / len(returns)
            )
            * 100,
            2,
        )

    return {
        "total_return": total_return,
        "max_drawdown": max_drawdown,
        "sharpe": sharpe,
        "profit_factor": profit_factor,
        "win_rate": win_rate,
    }