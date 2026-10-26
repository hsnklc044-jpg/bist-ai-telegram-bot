"""
QuantBIST
Is a backtest result distinguishable from luck?

- excess_returns(): daily strategy return minus XU100's, same days.
- bootstrap_excess(): moving-block bootstrap of the mean daily excess,
  annualised. Blocks (default 21 sessions, about a month) keep the
  autocorrelation and volatility clusters that an ordinary bootstrap
  would destroy, so the interval is not falsely narrow.
- When k strategies are compared, the interval is widened to the
  Bonferroni level 1 - alpha / k: testing many rules and keeping the best
  one is the most common way to fool oneself (data snooping).

A rule counts as "beating XU100" only when the whole interval is above
zero. Anything else is reported as not significant, whatever its point
estimate.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

TRADING_DAYS = 252
BLOCK = 21
SAMPLES = 2000
ALPHA = 0.05


@dataclass
class ExcessStats:
    mean: float  # annualised mean daily excess return (arithmetic)
    low: float
    high: float
    level: float
    days: int

    @property
    def significant(self) -> bool:
        return self.low > 0

    @property
    def verdict(self) -> str:
        if self.significant:
            return "XU100'den anlamlı yüksek"
        if self.high < 0:
            return "XU100'den anlamlı düşük"
        return "anlamlı değil"


def excess_returns(equity: pd.Series, benchmark_close: pd.Series) -> pd.Series:
    joined = pd.concat({"s": equity, "b": benchmark_close}, axis=1, sort=True).dropna()
    daily = joined.pct_change().dropna()
    return daily["s"] - daily["b"]


def bonferroni_level(tests: int, alpha: float = ALPHA) -> float:
    return 1 - alpha / max(tests, 1)


def bootstrap_excess(
    excess: pd.Series,
    level: float = 1 - ALPHA,
    block: int = BLOCK,
    samples: int = SAMPLES,
    seed: int = 0,
) -> ExcessStats | None:
    values = np.asarray(excess.dropna(), dtype=float)
    n = len(values)
    if n < 2 * block:
        return None

    rng = np.random.default_rng(seed)
    blocks = int(np.ceil(n / block))
    # circular moving blocks: each sample is `blocks` random starting points
    starts = rng.integers(0, n, size=(samples, blocks))
    index = (starts[:, :, None] + np.arange(block)) % n
    means = values[index.reshape(samples, -1)[:, :n]].mean(axis=1)

    tail = (1 - level) / 2
    low, high = np.quantile(means, [tail, 1 - tail])

    return ExcessStats(
        mean=float(values.mean() * TRADING_DAYS),
        low=float(low * TRADING_DAYS),
        high=float(high * TRADING_DAYS),
        level=level,
        days=n,
    )


__all__ = ["ExcessStats", "bonferroni_level", "bootstrap_excess", "excess_returns"]
