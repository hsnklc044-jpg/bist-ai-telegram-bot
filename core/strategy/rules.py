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


def low_volatility_signals(
    frames: dict[str, pd.DataFrame],
    window: int = 60,
    top_n: int = 10,
    eligible: pd.DataFrame | None = None,
) -> dict[str, pd.DataFrame]:
    """
    Aşama 3 H1 (docs/RESEARCH_LOG.md, fixed before testing): on the last session of each
    month, the `top_n` stocks with the lowest standard deviation of their last `window`
    daily returns; held until the next month end. With `eligible`, only stocks eligible
    on that day (point-in-time BIST 100 members) are ranked. Orders fill at the next
    session's open (the first session of the month), as for every rule.
    """

    closes = _closes(frames)
    volatility = closes.pct_change().rolling(window, min_periods=window).std()
    if eligible is not None:
        ok = eligible.reindex(index=closes.index, columns=closes.columns).ffill().fillna(False).astype(bool)
        volatility = volatility.where(ok)

    month_end = closes.index.to_series().groupby(closes.index.to_period("M")).max()
    rebalance = closes.index.isin(month_end.values)

    in_top = pd.DataFrame(index=closes.index, columns=closes.columns, dtype="float")
    for day in closes.index[rebalance]:
        chosen = set(volatility.loc[day].dropna().sort_values().index[:top_n])
        in_top.loc[day] = [1.0 if s in chosen else 0.0 for s in closes.columns]
    in_top = in_top.ffill().fillna(0.0).astype(bool)

    result = {}
    for symbol in closes.columns:
        own = frames[symbol].index
        hold = in_top[symbol].reindex(own).fillna(False)
        result[symbol] = pd.DataFrame(
            {"enter": hold, "exit": ~hold, "rank": -volatility[symbol].reindex(own).fillna(1.0)},
            index=own,
        )

    return result


def session_calendar(index: pd.DatetimeIndex, ahead_days: int = 45) -> pd.DatetimeIndex:
    """
    Past sessions are the candles themselves; after the last candle, the published
    holiday calendar (weekdays that are not full holidays). Only dates are used,
    never prices, so a rule timed by it does not look ahead.
    """

    from core.market.calendar import is_session_day

    index = pd.DatetimeIndex(index).normalize()
    future = pd.date_range(index[-1] + pd.Timedelta(days=1), periods=ahead_days, freq="D")
    future = [d for d in future if is_session_day(d.date())]
    return index.append(pd.DatetimeIndex(future)).unique().sort_values()


def _month_last_sessions(calendar: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(calendar.to_series().groupby(calendar.to_period("M")).max().values)


def index_trend_signals(benchmark: pd.DataFrame, window: int = 200) -> pd.DataFrame:
    """
    Aşama 3 H2 (docs/RESEARCH_LOG.md, fixed before testing): on each month's last
    session, hold the index for the next month if it closes above its `window`-session
    average; otherwise cash. Orders fill at the next open (the month's first session).
    """

    close = benchmark["close"]
    above = close > close.rolling(window, min_periods=window).mean()
    calendar = session_calendar(close.index)
    last = close.index[close.index.normalize().isin(_month_last_sessions(calendar)[:-1])]
    hold = pd.Series(float("nan"), index=close.index)
    hold.loc[last] = above.loc[last].astype(float)
    hold = hold.ffill().fillna(0.0).astype(bool)
    return pd.DataFrame({"enter": hold, "exit": ~hold, "rank": 0.0}, index=close.index)


def turn_of_month_signals(benchmark: pd.DataFrame, sessions: int = 3) -> pd.DataFrame:
    """
    Aşama 3 H3 (docs/RESEARCH_LOG.md, fixed before testing): hold the index over each
    month's last `sessions` and the next month's first `sessions` sessions, cash
    otherwise. The signal at a close is "the next session is in the window"; orders
    fill at that next session's open.
    """

    calendar = session_calendar(benchmark.index)
    series = calendar.to_series()
    month = calendar.to_period("M")
    from_start = series.groupby(month).cumcount() + 1
    from_end = series.groupby(month).cumcount(ascending=False) + 1
    in_window = pd.Series((from_start <= sessions).values | (from_end <= sessions).values, index=calendar)
    next_in_window = in_window.shift(-1, fill_value=False)
    hold = next_in_window.reindex(benchmark.index.normalize()).fillna(False).astype(bool)
    hold.index = benchmark.index
    return pd.DataFrame({"enter": hold, "exit": ~hold, "rank": 0.0}, index=benchmark.index)


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
    "low_volatility_signals",
    "session_calendar",
    "index_trend_signals",
    "turn_of_month_signals",
    "with_regime",
    "apply_rule",
]
