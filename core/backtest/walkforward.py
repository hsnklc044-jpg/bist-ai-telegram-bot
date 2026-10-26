"""
QuantBIST
Walk-forward test.

Parameters are chosen on a trailing in-sample window, then traded on
the following, unseen window. Only the out-of-sample windows are
stitched into the reported equity curve, so parameter tuning cannot
inflate the result.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd

from core.backtest.engine import BacktestConfig, compute_metrics, run_backtest

# A candidate maps a parameter dict to {symbol: signal frame}.
Candidate = Callable[[dict], dict[str, pd.DataFrame]]


@dataclass
class WalkForwardStep:
    train_start: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    params: dict
    train_sharpe: float
    test_return: float


@dataclass
class WalkForwardResult:
    equity: pd.Series
    steps: list[WalkForwardStep]
    metrics: dict


def walk_forward(
    frames: dict[str, pd.DataFrame],
    build_signals: Candidate,
    grid: list[dict],
    config: BacktestConfig,
    start: str,
    end: str | None = None,
    train_months: int = 24,
    test_months: int = 6,
    positions_key: str | None = "top_n",
) -> WalkForwardResult:
    calendar = pd.DatetimeIndex(
        sorted(set().union(*(df.index for df in frames.values() if not df.empty)))
    )
    last = pd.Timestamp(end) if end else calendar[-1]

    cache = {i: build_signals(params) for i, params in enumerate(grid)}

    def cfg(params):
        if positions_key and positions_key in params:
            return BacktestConfig(**{**config.__dict__, "max_positions": params[positions_key]})
        return config

    steps: list[WalkForwardStep] = []
    pieces: list[pd.Series] = []
    trades = []
    capital = config.initial_capital

    test_start = pd.Timestamp(start)
    while test_start < last:
        train_start = test_start - pd.DateOffset(months=train_months)
        test_end = min(test_start + pd.DateOffset(months=test_months) - pd.Timedelta(days=1), last)

        best_i, best_sharpe = 0, float("-inf")
        for i, params in enumerate(grid):
            train = run_backtest(
                frames, cache[i], cfg(params), start=train_start, end=test_start - pd.Timedelta(days=1)
            )
            sharpe = train.metrics.get("sharpe", float("-inf"))
            if sharpe is not None and sharpe > best_sharpe:
                best_i, best_sharpe = i, sharpe

        params = grid[best_i]
        test = run_backtest(
            frames,
            cache[best_i],
            BacktestConfig(**{**cfg(params).__dict__, "initial_capital": capital}),
            start=test_start,
            end=test_end,
        )

        if len(test.equity):
            pieces.append(test.equity)
            trades.extend(test.trades)
            capital = float(test.equity.iloc[-1])
            steps.append(
                WalkForwardStep(
                    train_start=train_start,
                    test_start=test_start,
                    test_end=test_end,
                    params=params,
                    train_sharpe=best_sharpe,
                    test_return=float(test.equity.iloc[-1] / test.equity.iloc[0] - 1),
                )
            )

        test_start = test_end + pd.Timedelta(days=1)

    equity = pd.concat(pieces) if pieces else pd.Series(dtype=float)
    equity = equity[~equity.index.duplicated(keep="last")]

    return WalkForwardResult(
        equity=equity,
        steps=steps,
        metrics=compute_metrics(equity, trades),
    )


__all__ = [
    "WalkForwardStep",
    "WalkForwardResult",
    "walk_forward",
]
