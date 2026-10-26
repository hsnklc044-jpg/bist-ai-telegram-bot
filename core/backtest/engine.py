"""
QuantBIST
Backtest engine (daily bars, long only).

Rules that keep the test honest:

- Decisions use only data up to the close of day t.
- Orders fill at the OPEN of day t+1, never at the close that
  produced the signal.
- Every fill pays commission and slippage (per side).
- A stop is checked against the day's low; a gap below the stop fills
  at the open, not at the stop price.
- A symbol without a candle on a day cannot be traded that day.
- Capital is split into `max_positions` equal slots; unused slots
  stay in cash. Cash earns nothing unless `cash` names a model from
  core.backtest.cash; sale proceeds then earn only after settlement
  (T+2 on BIST), and money used for a purchase stops earning on the
  trade day (conservative).
- Locked limit days (BIST ±10% price limit with no trading range:
  high == low) cannot be traded: a stock locked at the lower limit
  cannot be sold, one locked at the upper limit cannot be bought.
  Exits wait for the first tradable day.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

TRADING_DAYS = 252
LIMIT_MOVE = 0.095


@dataclass(frozen=True)
class BacktestConfig:
    initial_capital: float = 100_000.0
    max_positions: int = 5
    commission: float = 0.001
    slippage: float = 0.0005
    atr_stop: float | None = None
    max_holding_days: int | None = None
    respect_limit_locks: bool = True
    cash: object | None = None  # None = 0% (see core.backtest.cash)
    settlement_days: int = 2
    # Liquidity: a purchase may not exceed this share of the stock's average
    # daily turnover (close x volume, 20 sessions up to YESTERDAY). None = no cap.
    max_volume_share: float | None = None
    volume_window: int = 20


@dataclass
class Trade:
    symbol: str
    entry_date: pd.Timestamp
    entry_price: float
    exit_date: pd.Timestamp | None = None
    exit_price: float | None = None
    exit_reason: str = ""
    shares: float = 0.0
    stop: float | None = None

    @property
    def gross_return(self) -> float:
        return self.exit_price / self.entry_price - 1 if self.exit_price else 0.0

    @property
    def holding_days(self) -> int:
        return (self.exit_date - self.entry_date).days if self.exit_date is not None else 0


@dataclass
class BacktestResult:
    equity: pd.Series
    trades: list[Trade]
    exposure: pd.Series
    config: BacktestConfig
    metrics: dict = field(default_factory=dict)

    def trades_frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "symbol": t.symbol,
                    "entry_date": t.entry_date.date(),
                    "entry_price": round(t.entry_price, 4),
                    "exit_date": t.exit_date.date() if t.exit_date is not None else None,
                    "exit_price": round(t.exit_price, 4) if t.exit_price else None,
                    "return_pct": round(t.gross_return * 100, 2),
                    "days": t.holding_days,
                    "reason": t.exit_reason,
                }
                for t in self.trades
            ]
        )


# Signal function: given one symbol's candles, return a frame indexed
# like the candles with columns "enter" (bool), "exit" (bool) and
# "rank" (higher = preferred when slots are scarce). Values on day t
# may use only data up to and including day t.
SignalFn = Callable[[pd.DataFrame], pd.DataFrame]


def _atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    prev = df["close"].shift(1)
    tr = pd.concat(
        [df["high"] - df["low"], (df["high"] - prev).abs(), (df["low"] - prev).abs()],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()


def run_backtest(
    frames: dict[str, pd.DataFrame],
    signal_fn: SignalFn | Mapping[str, pd.DataFrame],
    config: BacktestConfig | None = None,
    start: pd.Timestamp | str | None = None,
    end: pd.Timestamp | str | None = None,
) -> BacktestResult:
    config = config or BacktestConfig()
    cost = config.commission + config.slippage

    if isinstance(signal_fn, Mapping):
        signals = {s: signal_fn[s] for s in frames if s in signal_fn}
    else:
        signals = {s: signal_fn(df) for s, df in frames.items() if not df.empty}
    atrs = {s: _atr(df) for s, df in frames.items() if not df.empty}

    # Plain dict lookups instead of DataFrame.loc inside the daily loop.
    bars_by_day: dict[pd.Timestamp, dict[str, tuple]] = {}
    for s, df in frames.items():
        for row in df[["open", "high", "low", "close"]].itertuples():
            bars_by_day.setdefault(row.Index, {})[s] = (row.open, row.high, row.low, row.close)

    enter_on: dict[pd.Timestamp, list[tuple[float, str]]] = {}
    exit_on: dict[pd.Timestamp, set[str]] = {}
    for s, sig in signals.items():
        if sig is None or sig.empty:
            continue
        enters = sig.index[sig["enter"].fillna(False).astype(bool)]
        for day in enters:
            enter_on.setdefault(day, []).append((float(sig.at[day, "rank"]), s))
        exits = sig.index[sig["exit"].fillna(False).astype(bool)]
        for day in exits:
            exit_on.setdefault(day, set()).add(s)

    atr_prev = {s: a.shift(1).to_dict() for s, a in atrs.items()} if config.atr_stop else {}

    turnover_prev: dict[str, dict] = {}
    if config.max_volume_share is not None:
        for s, df in frames.items():
            turnover = (df["close"] * df["volume"].where(df["volume"] > 0)).rolling(
                config.volume_window, min_periods=config.volume_window
            ).mean()
            turnover_prev[s] = turnover.shift(1).to_dict()

    locked_down: set[tuple[pd.Timestamp, str]] = set()
    locked_up: set[tuple[pd.Timestamp, str]] = set()
    if config.respect_limit_locks:
        for s, df in frames.items():
            change = df["close"].pct_change()
            flat = df["high"] <= df["low"]
            for day in df.index[flat & (change <= -LIMIT_MOVE)]:
                locked_down.add((day, s))
            for day in df.index[flat & (change >= LIMIT_MOVE)]:
                locked_up.add((day, s))

    calendar = sorted(set().union(*(df.index for df in frames.values() if not df.empty)))
    calendar = pd.DatetimeIndex(calendar)
    if start is not None:
        calendar = calendar[calendar >= pd.Timestamp(start)]
    if end is not None:
        calendar = calendar[calendar <= pd.Timestamp(end)]

    cash = config.initial_capital
    open_trades: dict[str, Trade] = {}
    closed: list[Trade] = []
    pending_entries: list[str] = []
    pending_exits: dict[str, str] = {}
    last_close: dict[str, float] = {}

    equity_points = []
    exposure_points = []

    # Cash interest (only when a cash model is set).
    unsettled: list[tuple[int, float]] = []  # (calendar index when settled, amount)
    cash_interest = 0.0
    cash_missing_days = 0
    prev_day = None

    def settle_later(i: int, amount: float) -> None:
        if config.cash is not None and config.settlement_days > 0:
            unsettled.append((i + config.settlement_days, amount))

    for i, day in enumerate(calendar):
        bars = bars_by_day.get(day, {})

        # 0. Interest on settled cash held overnight (prev close -> today).
        if config.cash is not None and prev_day is not None:
            growth = config.cash.growth(prev_day, day)
            earning = max(0.0, cash - sum(a for _, a in unsettled))
            interest = earning * (growth.factor - 1)
            cash += interest
            cash_interest += interest
            cash_missing_days += growth.missing_days
        unsettled = [(when, a) for when, a in unsettled if when > i]
        prev_day = day

        # 1. Fill orders decided at yesterday's close, at today's open.
        for symbol, reason in list(pending_exits.items()):
            if symbol in bars and symbol in open_trades and (day, symbol) not in locked_down:
                trade = open_trades.pop(symbol)
                price = bars[symbol][0] * (1 - cost)
                cash += trade.shares * price
                settle_later(i, trade.shares * price)
                trade.exit_date, trade.exit_price, trade.exit_reason = day, price, reason
                closed.append(trade)
                del pending_exits[symbol]

        # Slot size from equity at the previous close, the same for all of today's entries.
        slot = (
            cash
            + sum(t.shares * last_close.get(s, t.entry_price) for s, t in open_trades.items())
        ) / config.max_positions

        for symbol in pending_entries:
            if symbol not in bars or symbol in open_trades or (day, symbol) in locked_up:
                continue
            if len(open_trades) >= config.max_positions:
                break
            budget = min(slot, cash)
            if budget <= 0:
                break
            if config.max_volume_share is not None:
                turnover = turnover_prev.get(symbol, {}).get(day)
                if turnover is None or np.isnan(turnover):
                    continue  # no liquidity history yet: do not trade
                budget = min(budget, config.max_volume_share * turnover)
            price = bars[symbol][0] * (1 + cost)
            trade = Trade(symbol=symbol, entry_date=day, entry_price=price, shares=budget / price)
            if config.atr_stop is not None:
                atr = atr_prev[symbol].get(day)
                if atr is not None and not np.isnan(atr):
                    trade.stop = bars[symbol][0] - config.atr_stop * atr
            cash -= budget
            open_trades[symbol] = trade
        pending_entries = []

        # 2. Intraday stops.
        for symbol, trade in list(open_trades.items()):
            if trade.stop is None or symbol not in bars or (day, symbol) in locked_down:
                continue
            bar_open, _, bar_low, _ = bars[symbol]
            if bar_low <= trade.stop:
                fill = min(bar_open, trade.stop) * (1 - cost)
                cash += trade.shares * fill
                settle_later(i, trade.shares * fill)
                trade.exit_date, trade.exit_price, trade.exit_reason = day, fill, "stop"
                closed.append(open_trades.pop(symbol))
                pending_exits.pop(symbol, None)

        # 3. Mark to market.
        for symbol, bar in bars.items():
            last_close[symbol] = float(bar[3])

        invested = sum(t.shares * last_close.get(s, t.entry_price) for s, t in open_trades.items())
        equity = cash + invested
        equity_points.append((day, equity))
        exposure_points.append((day, invested / equity if equity else 0.0))

        # 4. Decide tomorrow's orders from today's close.
        exiting = exit_on.get(day, set())
        for symbol, trade in open_trades.items():
            if symbol in exiting:
                pending_exits[symbol] = "signal"
            elif (
                config.max_holding_days
                and (day - trade.entry_date).days >= config.max_holding_days
            ):
                pending_exits[symbol] = "time"

        candidates = [(r, s) for r, s in enter_on.get(day, []) if s not in open_trades]

        candidates.sort(reverse=True)
        free = config.max_positions - (len(open_trades) - len(pending_exits))
        pending_entries = [s for _, s in candidates[: max(free, 0)]]

    # Close what is still open at the last close (marked, not traded).
    for symbol, trade in open_trades.items():
        trade.exit_date = calendar[-1]
        trade.exit_price = last_close.get(symbol, trade.entry_price) * (1 - cost)
        trade.exit_reason = "end"
        closed.append(trade)

    equity_series = pd.Series(dict(equity_points), name="equity")
    exposure_series = pd.Series(dict(exposure_points), name="exposure")

    result = BacktestResult(
        equity=equity_series,
        trades=sorted(closed, key=lambda t: t.entry_date),
        exposure=exposure_series,
        config=config,
    )
    result.metrics = compute_metrics(equity_series, result.trades, exposure_series)
    if config.cash is not None:
        result.metrics["cash_model"] = repr(config.cash)
        result.metrics["cash_interest"] = cash_interest
        result.metrics["cash_missing_days"] = cash_missing_days

    return result


def compute_metrics(
    equity: pd.Series,
    trades: list[Trade] | None = None,
    exposure: pd.Series | None = None,
) -> dict:
    trades = trades or []

    if len(equity) < 2:
        return {}

    returns = equity.pct_change().dropna()
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    total = equity.iloc[-1] / equity.iloc[0] - 1
    cagr = (1 + total) ** (1 / years) - 1 if years > 0 and total > -1 else float("nan")

    vol = returns.std() * np.sqrt(TRADING_DAYS)
    downside = returns[returns < 0].std() * np.sqrt(TRADING_DAYS)
    sharpe = returns.mean() / returns.std() * np.sqrt(TRADING_DAYS) if returns.std() else 0.0
    sortino = returns.mean() * TRADING_DAYS / downside if downside else 0.0

    drawdown = equity / equity.cummax() - 1
    max_dd = drawdown.min()

    rets = [t.gross_return for t in trades]
    wins = [r for r in rets if r > 0]
    losses = [r for r in rets if r <= 0]
    gross_profit = sum(t.shares * (t.exit_price - t.entry_price) for t in trades if t.gross_return > 0)
    gross_loss = -sum(t.shares * (t.exit_price - t.entry_price) for t in trades if t.gross_return <= 0)

    return {
        "start": equity.index[0].date().isoformat(),
        "end": equity.index[-1].date().isoformat(),
        "total_return": total,
        "cagr": cagr,
        "volatility": vol,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown": max_dd,
        "calmar": cagr / abs(max_dd) if max_dd else float("nan"),
        "trades": len(trades),
        "win_rate": len(wins) / len(rets) if rets else float("nan"),
        "avg_win": float(np.mean(wins)) if wins else float("nan"),
        "avg_loss": float(np.mean(losses)) if losses else float("nan"),
        "profit_factor": gross_profit / gross_loss if gross_loss else float("nan"),
        "avg_holding_days": float(np.mean([t.holding_days for t in trades])) if trades else float("nan"),
        "exposure": float(exposure.mean()) if exposure is not None and len(exposure) else float("nan"),
    }


def buy_and_hold(
    frames: dict[str, pd.DataFrame],
    initial_capital: float = 100_000.0,
    start: pd.Timestamp | str | None = None,
    end: pd.Timestamp | str | None = None,
) -> pd.Series:
    """Equal-weight buy and hold of all symbols (no rebalancing)."""

    closes = pd.concat({s: df["close"] for s, df in frames.items() if not df.empty}, axis=1, sort=True)
    if start is not None:
        closes = closes[closes.index >= pd.Timestamp(start)]
    if end is not None:
        closes = closes[closes.index <= pd.Timestamp(end)]
    closes = closes.ffill().dropna(axis=1, how="all")
    first = closes.bfill().iloc[0]
    growth = closes.ffill().fillna(first) / first
    curve = growth.mean(axis=1) * initial_capital

    return curve.rename("equity")


__all__ = [
    "BacktestConfig",
    "BacktestResult",
    "Trade",
    "SignalFn",
    "run_backtest",
    "compute_metrics",
    "buy_and_hold",
    "LIMIT_MOVE",
]
