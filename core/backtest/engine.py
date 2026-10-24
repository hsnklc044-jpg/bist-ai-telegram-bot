"""
QuantBIST
Backtest engine.

Long-only simulation of the live signal on daily candles.

Rules (BacktestConfig holds the numbers):

- A BUY / STRONG BUY score after a session closes opens a position at
  the next session's open. Nothing is ever filled at the close that
  produced the signal: that price was not tradable any more.
- Stop and target are fixed at entry from the signal day's ATR, the
  same levels /analyze shows (stop = entry - 2 ATR, target_2 = +4 ATR).
  target_atr=None removes the target. With trailing_atr the stop
  follows the highest close (highest close - trailing_atr x entry ATR);
  it only ever moves up and takes effect from the next candle.
- Stop and target are checked on every candle, the entry day included.
  A gap through a level fills at the open. When one candle touches
  both, the stop is assumed to come first.
- A SELL score (or the holding limit) closes the position at the next
  open. With hold_in_uptrend these two exits are skipped while the
  market is in an uptrend (the `uptrend` series, known at that close).
  A position still open on the last candle is closed at its close.
- Idle cash earns cash_rate (annual), compounded per trading day.
- Every fill pays commission and slippage.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import pandas as pd

from core.backtest.signals import score_history
from core.config.thresholds import SIGNAL_BUY, SIGNAL_SELL

TRADING_DAYS = 252


@dataclass(frozen=True)
class BacktestConfig:
    commission: float = 0.002
    slippage: float = 0.001
    stop_atr: float = 2.0
    target_atr: float | None = 4.0
    trailing_atr: float | None = None
    max_hold_days: int = 40
    hold_in_uptrend: bool = False
    entry_score: float = SIGNAL_BUY
    exit_score: float = SIGNAL_SELL
    cash_rate: float = 0.0


@dataclass
class Trade:
    symbol: str
    entry_date: pd.Timestamp
    entry_price: float
    stop: float
    target: float
    atr: float = 0.0
    highest: float = 0.0
    exit_date: pd.Timestamp | None = None
    exit_price: float | None = None
    reason: str = ""
    days: int = 0

    @property
    def gross_return(self) -> float:
        return self.exit_price / self.entry_price - 1


@dataclass
class Metrics:
    total_return: float
    cagr: float
    max_drawdown: float
    sharpe: float
    trades: int
    win_rate: float
    avg_trade: float
    profit_factor: float
    avg_days: float
    exposure: float
    buy_hold: float


@dataclass
class SymbolResult:
    symbol: str
    trades: list[Trade]
    equity: pd.Series
    metrics: Metrics
    signals: pd.DataFrame = field(repr=False)


def _fill(price: float, side: int, config: BacktestConfig) -> float:
    """Price actually paid (side=+1) or received (side=-1) after slippage."""

    return price * (1 + side * config.slippage)


def simulate(
    symbol: str,
    df: pd.DataFrame,
    config: BacktestConfig | None = None,
    signals: pd.DataFrame | None = None,
    uptrend: pd.Series | None = None,
) -> SymbolResult:
    """
    Run the strategy on one symbol. Equity starts at 1.0.

    `uptrend` is a boolean market-regime series; only used with
    config.hold_in_uptrend. Missing days count as no uptrend.
    """

    config = config or BacktestConfig()
    signals = score_history(df) if signals is None else signals

    if uptrend is None:
        rising = [False] * len(df)
    else:
        rising = uptrend.reindex(df.index).ffill().fillna(False).astype(bool).tolist()

    daily_rate = (1 + config.cash_rate) ** (1 / TRADING_DAYS) - 1
    target_atr = config.target_atr if config.target_atr else math.inf

    opens = df["open"].to_numpy(dtype=float)
    highs = df["high"].to_numpy(dtype=float)
    lows = df["low"].to_numpy(dtype=float)
    closes = df["close"].to_numpy(dtype=float)
    scores = signals["score"].to_numpy(dtype=float)
    atrs = signals["atr"].to_numpy(dtype=float)
    dates = df.index

    cash = 1.0
    shares = 0.0
    trade: Trade | None = None
    trades: list[Trade] = []
    equity = []
    in_market = 0
    pending_entry_atr: float | None = None
    pending_exit: str | None = None

    def close_trade(i: int, price: float, reason: str) -> None:
        nonlocal cash, shares, trade
        fill = _fill(price, -1, config)
        cash = shares * fill * (1 - config.commission)
        shares = 0.0
        trade.exit_date = dates[i]
        trade.exit_price = fill
        trade.reason = reason
        trades.append(trade)
        trade = None

    for i in range(len(df)):
        if i > 0:
            cash *= 1 + daily_rate

        if trade is not None and pending_exit:
            close_trade(i, opens[i], pending_exit)
        pending_exit = None

        if trade is None and pending_entry_atr is not None:
            fill = _fill(opens[i], +1, config)
            shares = cash * (1 - config.commission) / fill
            cash = 0.0
            trade = Trade(
                symbol=symbol,
                entry_date=dates[i],
                entry_price=fill,
                stop=fill - config.stop_atr * pending_entry_atr,
                target=fill + target_atr * pending_entry_atr,
                atr=pending_entry_atr,
                highest=fill,
            )
        pending_entry_atr = None

        if trade is not None:
            trade.days += 1

            if opens[i] <= trade.stop:
                close_trade(i, opens[i], "stop")
            elif lows[i] <= trade.stop:
                close_trade(i, trade.stop, "stop")
            elif opens[i] >= trade.target:
                close_trade(i, opens[i], "target")
            elif highs[i] >= trade.target:
                close_trade(i, trade.target, "target")

        if trade is not None:
            in_market += 1

            if config.trailing_atr:
                trade.highest = max(trade.highest, closes[i])
                trade.stop = max(trade.stop, trade.highest - config.trailing_atr * trade.atr)

        equity.append(cash + shares * closes[i])

        if i == len(df) - 1 or math.isnan(scores[i]):
            continue

        if trade is not None:
            if config.hold_in_uptrend and rising[i]:
                pass
            elif scores[i] <= config.exit_score:
                pending_exit = "signal"
            elif trade.days >= config.max_hold_days:
                pending_exit = "time"
        elif scores[i] >= config.entry_score and atrs[i] > 0:
            pending_entry_atr = atrs[i]

    if trade is not None:
        close_trade(len(df) - 1, closes[-1], "end")
        equity[-1] = cash

    curve = pd.Series(equity, index=dates, name=symbol)

    # Buy & hold over the period the strategy could trade (after warm-up).
    first = signals["score"].first_valid_index()
    start = dates.get_loc(first) if first is not None else 0
    buy_hold = float(closes[-1] / closes[start] - 1) if len(closes) else 0.0

    metrics = compute_metrics(curve, trades, in_market / max(len(df), 1), buy_hold, config)

    return SymbolResult(
        symbol=symbol,
        trades=trades,
        equity=curve,
        metrics=metrics,
        signals=signals,
    )


def max_drawdown(curve: pd.Series) -> float:
    if curve.empty:
        return 0.0

    return float((curve / curve.cummax() - 1).min())


def curve_stats(curve: pd.Series) -> tuple[float, float, float, float]:
    """total return, CAGR, max drawdown, Sharpe (rf = 0) of an equity curve."""

    if len(curve) < 2 or curve.iloc[0] <= 0:
        return 0.0, 0.0, 0.0, 0.0

    total = float(curve.iloc[-1] / curve.iloc[0] - 1)
    years = len(curve) / TRADING_DAYS
    cagr = (1 + total) ** (1 / years) - 1 if total > -1 else -1.0

    daily = curve.pct_change().dropna()
    std = daily.std()
    sharpe = float(daily.mean() / std * math.sqrt(TRADING_DAYS)) if std > 0 else 0.0

    return total, cagr, max_drawdown(curve), sharpe


def trade_stats(trades: list[Trade], config: BacktestConfig | None = None) -> dict:
    """Win rate etc. Net trade returns include both sides' costs."""

    config = config or BacktestConfig()
    cost = (1 - config.commission) ** 2
    returns = [(1 + t.gross_return) * cost - 1 for t in trades]

    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r <= 0]
    loss_sum = -sum(losses)

    return {
        "trades": len(returns),
        "win_rate": len(wins) / len(returns) if returns else 0.0,
        "avg_trade": sum(returns) / len(returns) if returns else 0.0,
        "profit_factor": sum(wins) / loss_sum if loss_sum > 0 else math.inf if wins else 0.0,
        "avg_days": sum(t.days for t in trades) / len(trades) if trades else 0.0,
    }


def compute_metrics(
    curve: pd.Series,
    trades: list[Trade],
    exposure: float,
    buy_hold: float,
    config: BacktestConfig,
) -> Metrics:
    total, cagr, drawdown, sharpe = curve_stats(curve)

    return Metrics(
        total_return=total,
        cagr=cagr,
        max_drawdown=drawdown,
        sharpe=sharpe,
        exposure=exposure,
        buy_hold=buy_hold,
        **trade_stats(trades, config),
    )


__all__ = [
    "BacktestConfig",
    "Metrics",
    "SymbolResult",
    "Trade",
    "curve_stats",
    "max_drawdown",
    "simulate",
    "trade_stats",
]
