"""
QuantBIST
Drawdown diagnosis.

    python -m core.backtest.diagnose
    python -m core.backtest.diagnose --start 2023-08-01 --positions 10

Explains the deepest drawdown of the momentum rule from the research
report: when it happened, which stocks lost the money, the worst trades,
and whether any of those trades held a stock through a daily move that
BIST's ±10% price limit cannot produce (a data error, not a real loss).

A move counts as impossible when it exceeds the limit compounded over
the business days since the previous candle, and is not a market-wide
move (such as the February 2023 reopening).
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass

import pandas as pd

from core.backtest.engine import BacktestConfig, BacktestResult, Trade, run_backtest
from core.backtest.research import DEFAULT_START
from core.backtest.run import load_frames, tradable_symbols
from core.market.quality import limit_breaches, market_wide_moves
from core.strategy.rules import momentum_signals


@dataclass
class Drawdown:
    peak: pd.Timestamp
    trough: pd.Timestamp
    depth: float


def deepest_drawdown(equity: pd.Series) -> Drawdown:
    drawdown = equity / equity.cummax() - 1
    trough = drawdown.idxmin()
    peak = equity.loc[:trough].idxmax()

    return Drawdown(peak=peak, trough=trough, depth=float(drawdown.min()))


def _overlaps(trade: Trade, start: pd.Timestamp, end: pd.Timestamp) -> bool:
    exit_date = trade.exit_date or end
    return trade.entry_date <= end and exit_date >= start


def _pnl_in_window(
    trade: Trade, frames: dict[str, pd.DataFrame], start: pd.Timestamp, end: pd.Timestamp
) -> float:
    """TL gained or lost by one trade between start and end (marked to close)."""

    close = frames[trade.symbol]["close"]
    first = max(trade.entry_date, start)
    last = min(trade.exit_date or end, end)

    begin = trade.entry_price if first == trade.entry_date else close.asof(first)
    finish = trade.exit_price if trade.exit_date and last == trade.exit_date else close.asof(last)

    return trade.shares * (finish - begin)


def diagnose(
    result: BacktestResult,
    frames: dict[str, pd.DataFrame],
    worst: int = 15,
) -> str:
    dd = deepest_drawdown(result.equity)
    market_wide = market_wide_moves(frames)

    contribution: dict[str, float] = defaultdict(float)
    for trade in result.trades:
        if _overlaps(trade, dd.peak, dd.trough):
            contribution[trade.symbol] += _pnl_in_window(trade, frames, dd.peak, dd.trough)

    loss = result.equity.loc[dd.peak] - result.equity.loc[dd.trough]

    lines = [
        f"En derin düşüş: {dd.depth:+.1%} ({dd.peak.date()} zirve → {dd.trough.date()} dip)",
        f"Kayıp: {loss:,.0f} TL",
        "",
        "Düşüş döneminde kâr/zarar (en kötü 10 hisse):",
    ]

    for symbol, pnl in sorted(contribution.items(), key=lambda kv: kv[1])[:10]:
        share = pnl / -loss if loss else 0.0
        lines.append(f"  {symbol:<10} {pnl:>12,.0f} TL  (kayba katkı %{share * 100:.0f})")

    lines += ["", f"En kötü {worst} işlem (tüm dönem):"]

    flagged_total = 0
    for trade in sorted(result.trades, key=lambda t: t.gross_return)[:worst]:
        df = frames[trade.symbol]
        held = df.loc[trade.entry_date : trade.exit_date or df.index[-1]]
        bad = limit_breaches(held, market_wide)
        flagged_total += len(bad)
        note = "  ⚠ " + ", ".join(f"{d.date()} {r:+.0%}" for d, r in bad.items()) if len(bad) else ""
        exit_text = str(trade.exit_date.date()) if trade.exit_date else "açık"
        lines.append(
            f"  {trade.symbol:<10} {trade.entry_date.date()} → {exit_text:<10} "
            f"{trade.gross_return:+7.1%}{note}"
        )

    all_bad = {
        s: limit_breaches(df, market_wide) for s, df in frames.items()
    }
    all_bad = {s: b for s, b in all_bad.items() if len(b)}

    lines += [
        "",
        f"±%10 limitiyle açıklanamayan günlük hareketler (tüm hisseler): "
        f"{sum(len(b) for b in all_bad.values())} gün, {len(all_bad)} hisse",
    ]
    for symbol, bad in sorted(all_bad.items()):
        lines.append(
            f"  {symbol:<10} " + ", ".join(f"{d.date()} {r:+.0%}" for d, r in bad.items())
        )

    lines += [
        "",
        "⚠ işaretli işlemler veri hatası içeriyor olabilir; KAP'tan doğrulayıp "
        "data/corporate_actions.csv dosyasına ekleyin."
        if flagged_total
        else "En kötü işlemlerde ±%10 limitine aykırı hareket yok: kayıplar gerçek fiyat hareketi.",
    ]

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Explain the momentum rule's deepest drawdown.")
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument("--positions", type=int, default=10)
    parser.add_argument("--lookback", type=int, default=126)
    args = parser.parse_args(argv)

    symbols, _ = tradable_symbols()
    frames = load_frames(symbols)
    signals = momentum_signals(frames, args.lookback, top_n=args.positions)
    result = run_backtest(
        frames, signals, BacktestConfig(max_positions=args.positions), start=args.start
    )

    print(f"Momentum {args.lookback} gün, en iyi {args.positions} | {len(symbols)} hisse")
    print(diagnose(result, frames))


if __name__ == "__main__":
    main()
