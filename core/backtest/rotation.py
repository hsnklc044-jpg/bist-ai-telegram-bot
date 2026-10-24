"""
QuantBIST
Rotation strategy.

Always invested: every `rebalance_days` sessions the stocks are ranked
after the close and the top `top_n` are held in equal weight from the
next session's open. Unlike the timing strategy in engine.py there is
no waiting in cash (unless `regime_filter` is on and XU100 is below its
200-day average).

Ranking:
- score     the live /analyze score
- momentum  return over the last `momentum_days` sessions
- blend     average of the two percentile ranks

Only stocks with a candle and a score on the ranking day are eligible.
Rebalancing pays commission and slippage on the traded value only.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from core.backtest.engine import BacktestConfig
from core.infrastructure.logger import get_logger

logger = get_logger(__name__)

RANKINGS = ("score", "momentum", "blend")


@dataclass(frozen=True)
class RotationConfig:
    top_n: int = 5
    ranking: str = "blend"
    rebalance_days: int = 21
    momentum_days: int = 126
    regime_filter: bool = False
    commission: float = BacktestConfig.commission
    slippage: float = BacktestConfig.slippage


@dataclass
class Rebalance:
    date: pd.Timestamp
    holdings: list[str]
    turnover: float


@dataclass
class RotationResult:
    config: RotationConfig
    equity: pd.Series
    rebalances: list[Rebalance]

    @property
    def trades(self) -> int:
        """Number of buys (a stock entering the portfolio)."""

        count = 0
        previous: set[str] = set()

        for r in self.rebalances:
            count += len(set(r.holdings) - previous)
            previous = set(r.holdings)

        return count

    @property
    def exposure(self) -> float:
        held = sum(1 for r in self.rebalances if r.holdings)
        return held / len(self.rebalances) if self.rebalances else 0.0

    @property
    def holdings(self) -> list[str]:
        return self.rebalances[-1].holdings if self.rebalances else []


def rank_table(
    closes: pd.DataFrame,
    scores: pd.DataFrame,
    candles: pd.DataFrame,
    config: RotationConfig,
) -> pd.DataFrame:
    """Ranking value per day and stock (higher is better); NaN = not eligible."""

    if config.ranking not in RANKINGS:
        raise ValueError(f"Unknown ranking: {config.ranking}")

    momentum = closes.pct_change(config.momentum_days, fill_method=None)
    eligible = candles & scores.notna()

    if config.ranking == "score":
        value = scores
    elif config.ranking == "momentum":
        value = momentum
    else:
        eligible &= momentum.notna()
        value = (scores.rank(axis=1, pct=True) + momentum.rank(axis=1, pct=True)) / 2

    return value.where(eligible)


def rotate(
    prices: dict[str, pd.DataFrame],
    signals: dict[str, pd.DataFrame],
    config: RotationConfig | None = None,
    uptrend: pd.Series | None = None,
    start: pd.Timestamp | None = None,
) -> RotationResult:
    """Simulate the rotation. Equity starts at 1.0 on `start`."""

    config = config or RotationConfig()

    closes_raw = pd.concat({s: df["close"] for s, df in prices.items()}, axis=1).sort_index()
    opens_raw = pd.concat({s: df["open"] for s, df in prices.items()}, axis=1).sort_index()
    candles = closes_raw.notna()
    closes = closes_raw.ffill()
    opens = opens_raw.ffill()
    scores = pd.concat({s: sig["score"] for s, sig in signals.items()}, axis=1).reindex(
        closes.index
    )

    ranks = rank_table(closes, scores, candles, config)

    if start is not None:
        closes, opens, ranks = (f[f.index >= start] for f in (closes, opens, ranks))

    rising = (
        uptrend.reindex(closes.index).ffill().fillna(False).astype(bool)
        if uptrend is not None
        else pd.Series(True, index=closes.index)
    )

    cost_rate = config.commission + config.slippage
    cash = 1.0
    shares: dict[str, float] = {}
    pending: list[str] | None = None
    rebalances: list[Rebalance] = []
    equity = []
    dates = closes.index

    for i, day in enumerate(dates):
        if pending is not None:
            value = cash + sum(n * opens.at[day, s] for s, n in shares.items())
            target = value / len(pending) if pending else 0.0

            traded = sum(
                abs((target if s in pending else 0.0) - shares.get(s, 0.0) * opens.at[day, s])
                for s in set(shares) | set(pending)
            )
            value -= traded * cost_rate
            target = value / len(pending) if pending else 0.0

            shares = {s: target / opens.at[day, s] for s in pending}
            cash = 0.0 if pending else value
            rebalances.append(Rebalance(day, pending, traded))
            pending = None

        equity.append(cash + sum(n * closes.at[day, s] for s, n in shares.items()))

        if i % config.rebalance_days or i == len(dates) - 1:
            continue

        if config.regime_filter and not rising.iloc[i]:
            pending = []
            continue

        row = ranks.iloc[i].dropna().sort_values(ascending=False)
        if row.empty:
            continue

        pending = list(row.index[: config.top_n])

    return RotationResult(
        config=config,
        equity=pd.Series(equity, index=dates, name="rotation"),
        rebalances=rebalances,
    )


def current_picks(
    prices: dict[str, pd.DataFrame],
    signals: dict[str, pd.DataFrame],
    config: RotationConfig | None = None,
) -> pd.Series:
    """Today's ranking (best first), as the rotation would rebalance now."""

    config = config or RotationConfig()

    closes_raw = pd.concat({s: df["close"] for s, df in prices.items()}, axis=1).sort_index()
    scores = pd.concat({s: sig["score"] for s, sig in signals.items()}, axis=1).reindex(
        closes_raw.index
    )
    candles = closes_raw.notna()
    ranks = rank_table(closes_raw.ffill(), scores, candles, config)

    return ranks.iloc[-1].dropna().sort_values(ascending=False)


__all__ = [
    "RANKINGS",
    "Rebalance",
    "RotationConfig",
    "RotationResult",
    "current_picks",
    "rank_table",
    "rotate",
]
