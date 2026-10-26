"""
QuantBIST
Strategy research report.

    python -m core.backtest.research
    python -m core.backtest.research --start 2024-01-01

Compares, on the same stocks, costs and period:
- the bot's live signal (with and without the market regime filter)
- a trend rule
- cross-sectional momentum (fixed parameters, with/without regime)
- momentum with walk-forward parameter selection (out-of-sample only)
- equal-weight buy & hold of the same stocks, and XU100
"""

from __future__ import annotations

import argparse

import pandas as pd

from core.backtest.cash import parse_cash_option
from core.backtest.engine import BacktestConfig, buy_and_hold, compute_metrics, run_backtest
from core.backtest.run import load_frames, tradable_symbols
from core.backtest.walkforward import walk_forward
from core.market.universe import BENCHMARK
from core.strategy.rules import (
    apply_rule,
    momentum_signals,
    regime_filter,
    score_rule,
    trend_rule,
    with_regime,
)

DEFAULT_START = "2023-08-01"

GRID = [
    dict(lookback=lb, top_n=top, regime=rg)
    for lb in (63, 126, 252)
    for top in (5, 10, 15)
    for rg in (False, True)
]


def _pct(x) -> str:
    return "-" if x is None or pd.isna(x) else f"{x * 100:+.1f}%"


def _num(x) -> str:
    return "-" if x is None or pd.isna(x) else f"{x:.2f}"


def research_report(
    start: str = DEFAULT_START,
    end: str | None = None,
    positions: int = 10,
    cash=None,
) -> str:
    symbols, skipped = tradable_symbols()
    frames = load_frames(symbols)
    bench = load_frames([BENCHMARK])[BENCHMARK]
    regime = regime_filter(bench)

    base = BacktestConfig(max_positions=positions, cash=cash)
    rows: list[tuple[str, dict]] = []

    def add(name, signals, top=positions):
        cfg = BacktestConfig(**{**base.__dict__, "max_positions": top})
        rows.append((name, run_backtest(frames, signals, cfg, start=start, end=end).metrics))

    add("Bot sinyali", score_rule(70, 70))
    add("Bot sinyali + rejim filtresi", with_regime(apply_rule(score_rule(70, 70), frames), regime))
    add("Trend kuralı", trend_rule())
    add(f"Momentum 6 ay, en iyi {positions}", momentum_signals(frames, 126, top_n=positions))
    add(
        f"Momentum 6 ay, en iyi {positions} + rejim",
        momentum_signals(frames, 126, top_n=positions, regime=regime),
    )

    wf = walk_forward(
        frames,
        lambda p: momentum_signals(
            frames, lookback=p["lookback"], top_n=p["top_n"], regime=regime if p["regime"] else None
        ),
        GRID,
        base,
        start=start,
        end=end,
    )
    rows.append(("Momentum walk-forward (test dönemleri)", wf.metrics))

    window = wf.equity.index
    ew = buy_and_hold(frames, start=window[0], end=window[-1])
    xu = bench["close"].loc[window[0]: window[-1]]
    rows.append(("Eşit ağırlık al-tut (aynı hisseler)", compute_metrics(ew)))
    rows.append(("XU100 al-tut", compute_metrics(xu / xu.iloc[0] * base.initial_capital)))

    lines = [
        f"Dönem: {window[0].date()} – {window[-1].date()} | {len(symbols)} hisse | "
        f"komisyon %{base.commission * 100:.2f} + kayma %{base.slippage * 100:.2f} (her yön)",
        f"Nakit: {repr(cash) if cash is not None else 'faizsiz (%0)'}",
    ]
    if skipped:
        lines.append(f"Veri yok/sorunlu, dışarıda ({len(skipped)}): {', '.join(skipped)}")

    lines += [
        "",
        f"{'Strateji':<42} {'Toplam':>9} {'Yıllık':>8} {'MaxDD':>8} {'Sharpe':>6} {'İşlem':>6}",
    ]
    for name, m in rows:
        lines.append(
            f"{name:<42} {_pct(m.get('total_return')):>9} {_pct(m.get('cagr')):>8} "
            f"{_pct(m.get('max_drawdown')):>8} {_num(m.get('sharpe')):>6} {m.get('trades', 0)!s:>6}"
        )

    lines += ["", "Walk-forward adımları (24 ay eğitim → 6 ay test):"]
    for s in wf.steps:
        p = s.params
        lines.append(
            f"  {s.test_start.date()} – {s.test_end.date()}: {p['lookback']} gün, "
            f"en iyi {p['top_n']}, rejim {'açık' if p['regime'] else 'kapalı'} "
            f"| eğitim Sharpe {s.train_sharpe:.2f} | test {_pct(s.test_return)}"
        )

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="QuantBIST strategy research")
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument("--end", default=None)
    parser.add_argument("--positions", type=int, default=10)
    parser.add_argument("--cash", default=None, help="none | fixed:0.35 | rate:<csv> | fund:<csv>")
    args = parser.parse_args(argv)

    print(
        research_report(
            start=args.start,
            end=args.end,
            positions=args.positions,
            cash=parse_cash_option(args.cash),
        )
    )


if __name__ == "__main__":
    main()
