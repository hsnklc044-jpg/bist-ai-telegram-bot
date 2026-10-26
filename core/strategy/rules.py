"""
QuantBIST
Trading rules for the backtest.

Each rule turns one symbol's candles into enter / exit / rank columns.
"""

from __future__ import annotations

import pandas as pd
from ta.trend import EMAIndicator

from core.strategy.score import score_frame


def score_rule(enter_at: float = 70, exit_below: float = 70):
    """
    The live bot's signal: buy on BUY / STRONG BUY (score >= 70).

    exit_below = enter_at reproduces "hold while the bot says buy";
    a lower value adds hysteresis (fewer whipsaw trades).
    """

    def rule(df: pd.DataFrame) -> pd.DataFrame:
        frame = score_frame(df)
        score = frame["score"]

        return pd.DataFrame(
            {
                "enter": score >= enter_at,
                "exit": score < exit_below,
                "rank": score.fillna(0),
            },
            index=df.index,
        )

    rule.__name__ = f"score_{enter_at:g}_{exit_below:g}"
    return rule


def trend_rule(fast: int = 20, slow: int = 50, long: int = 200):
    """Baseline: hold while EMA fast > EMA slow and price > EMA long."""

    def rule(df: pd.DataFrame) -> pd.DataFrame:
        close = df["close"]
        ema_fast = EMAIndicator(close, window=fast).ema_indicator()
        ema_slow = EMAIndicator(close, window=slow).ema_indicator()
        ema_long = EMAIndicator(close, window=long).ema_indicator()

        up = (ema_fast > ema_slow) & (close > ema_long)

        return pd.DataFrame(
            {
                "enter": up,
                "exit": ~up,
                "rank": (close / ema_long - 1).fillna(0),
            },
            index=df.index,
        )

    rule.__name__ = f"trend_{fast}_{slow}_{long}"
    return rule


__all__ = [
    "score_rule",
    "trend_rule",
]


# ---------------------------------------------------------------------------
# Cross-sectional rules: they look at all symbols at once and return
# {symbol: frame with enter / exit / rank}.
# ---------------------------------------------------------------------------


def _closes(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    return pd.concat({s: df["close"] for s, df in frames.items() if not df.empty}, axis=1, sort=True)


def regime_filter(benchmark: pd.DataFrame, window: int = 200) -> pd.Series:
    """True while the benchmark closes above its `window`-day average."""

    close = benchmark["close"]
    average = close.rolling(window, min_periods=window).mean()

    return (close > average).fillna(False)


def momentum_signals(
    frames: dict[str, pd.DataFrame],
    lookback: int = 126,
    skip: int = 21,
    top_n: int = 5,
    regime: pd.Series | None = None,
    eligible: pd.DataFrame | None = None,
) -> dict[str, pd.DataFrame]:
    """
    Hold the `top_n` stocks with the best return over `lookback` days,
    ignoring the most recent `skip` days (short-term reversal).
    The ranking is refreshed on the last session of each month.

    With `regime`, positions are only held while regime is True.
    With `eligible` (dates x symbols, e.g. point-in-time index membership),
    only stocks eligible on the rebalance day are ranked.
    """

    closes = _closes(frames)
    momentum = closes.shift(skip) / closes.shift(skip + lookback) - 1
    if eligible is not None:
        ok = eligible.reindex(index=closes.index, columns=closes.columns).ffill().fillna(False).astype(bool)
        momentum = momentum.where(ok)

    month_end = closes.index.to_series().groupby(closes.index.to_period("M")).max()
    rebalance = closes.index.isin(month_end.values)

    in_top = pd.DataFrame(index=closes.index, columns=closes.columns, dtype="float")
    for day in closes.index[rebalance]:
        ranks = momentum.loc[day].dropna().sort_values(ascending=False)
        chosen = set(ranks.index[:top_n])
        in_top.loc[day] = [1.0 if s in chosen else 0.0 for s in closes.columns]
    in_top = in_top.ffill().fillna(0.0).astype(bool)

    ok = (
        regime.reindex(closes.index).ffill().fillna(False).astype(bool)
        if regime is not None
        else pd.Series(True, index=closes.index)
    )

    result = {}
    for symbol in closes.columns:
        own = frames[symbol].index
        hold = (in_top[symbol] & ok).reindex(own).fillna(False)
        result[symbol] = pd.DataFrame(
            {
                "enter": hold,
                "exit": ~hold,
                "rank": momentum[symbol].reindex(own).fillna(-1.0),
            },
            index=own,
        )

    return result


def with_regime(
    signals: dict[str, pd.DataFrame],
    regime: pd.Series,
) -> dict[str, pd.DataFrame]:
    """Allow entries only in a good regime and exit everything in a bad one."""

    result = {}
    for symbol, sig in signals.items():
        ok = regime.reindex(sig.index).ffill().fillna(False).astype(bool)
        result[symbol] = sig.assign(enter=sig["enter"] & ok, exit=sig["exit"] | ~ok)

    return result


def apply_rule(rule, frames: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    return {s: rule(df) for s, df in frames.items() if not df.empty}


__all__ += [
    "regime_filter",
    "momentum_signals",
    "with_regime",
    "apply_rule",
]
