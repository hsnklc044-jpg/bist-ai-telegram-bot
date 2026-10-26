"""
QuantBIST
Strategy research report.

    python -m core.backtest.research
    python -m core.backtest.research --start 2024-01-01
    python -m core.backtest.research --universe today   # biased comparison only

Compares, on the same stocks, costs and period:
- the bot's live signal (with and without the market regime filter)
- a trend rule
- cross-sectional momentum (fixed parameters, with/without regime)
- momentum with walk-forward parameter selection (out-of-sample only)
- equal-weight buy & hold of the same stocks (today's list only), and XU100

The default universe is point-in-time BIST 100 membership: on each day
only that day's members can be bought. Each strategy's daily excess
return over XU100 gets a block-bootstrap confidence interval, widened
for the number of strategies tested (core/backtest/stats.py).
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from core.backtest.cash import parse_cash_option
from core.backtest.engine import BacktestConfig, buy_and_hold, compute_metrics, run_backtest
from core.backtest.run import load_frames, tradable_symbols
from core.backtest.stats import bonferroni_level, bootstrap_excess, excess_returns
from core.backtest.walkforward import walk_forward
from core.market.universe import BENCHMARK
from core.strategy.filters import apply_eligibility
from core.strategy.rules import (
    apply_rule,
    momentum_signals,
    regime_filter,
    score_rule,
    trend_rule,
    with_regime,
)

DEFAULT_START = "2023-08-01"
# above this share of former members without prices the point-in-time result is flagged
MAX_MISSING_SHARE = 0.10

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


def _universe(universe: str):
    """Symbols, skipped symbols, and the eligibility panel (None for today's list)."""

    if universe == "today":
        symbols, skipped = tradable_symbols()
        return load_frames(symbols), skipped, None

    from core.market.membership import ever_members, membership_panel

    symbols, skipped = tradable_symbols(ever_members())
    frames = {s: df for s, df in load_frames(symbols).items() if not df.empty}
    index = pd.DatetimeIndex(sorted(set().union(*(df.index for df in frames.values()))))
    return frames, skipped, membership_panel(index, list(frames))


def _window_return(close: pd.Series, start, end) -> float:
    part = close.loc[start:end]
    return float(part.iloc[-1] / part.iloc[0] - 1) if len(part) > 1 else float("nan")


def research_report(
    start: str = DEFAULT_START,
    end: str | None = None,
    positions: int = 10,
    cash=None,
    universe: str = "pit",
    seed: int = 0,
) -> str:
    frames, skipped, eligible = _universe(universe)
    bench = load_frames([BENCHMARK])[BENCHMARK]
    regime = regime_filter(bench)

    def gate(signals):
        return apply_eligibility(signals, eligible) if eligible is not None else signals

    base = BacktestConfig(max_positions=positions, cash=cash)
    rows: list[tuple[str, pd.Series, dict]] = []

    def add(name, signals, top=positions):
        cfg = BacktestConfig(**{**base.__dict__, "max_positions": top})
        res = run_backtest(frames, gate(signals), cfg, start=start, end=end)
        rows.append((name, res.equity, res.metrics))

    add("Bot sinyali", apply_rule(score_rule(70, 70), frames))
    add("Bot sinyali + rejim filtresi", with_regime(apply_rule(score_rule(70, 70), frames), regime))
    add("Trend kuralı", apply_rule(trend_rule(), frames))
    add(f"Momentum 6 ay, en iyi {positions}", momentum_signals(frames, 126, top_n=positions, eligible=eligible))
    add(
        f"Momentum 6 ay, en iyi {positions} + rejim",
        momentum_signals(frames, 126, top_n=positions, regime=regime, eligible=eligible),
    )

    wf = walk_forward(
        frames,
        lambda p: momentum_signals(
            frames,
            lookback=p["lookback"],
            top_n=p["top_n"],
            regime=regime if p["regime"] else None,
            eligible=eligible,
        ),
        GRID,
        base,
        start=start,
        end=end,
    )
    rows.append(("Momentum walk-forward (test dönemleri)", wf.equity, wf.metrics))
    tested = len(rows)

    window = wf.equity.index
    xu = bench["close"].loc[window[0]: window[-1]]
    if eligible is None:
        # today's list only: an equal-weight hold of stocks that are members
        # *now* is itself survivorship-biased, so it is not shown for "pit"
        ew = buy_and_hold(frames, start=window[0], end=window[-1])
        rows.append(("Eşit ağırlık al-tut (aynı hisseler)", ew, compute_metrics(ew)))
    rows.append(("XU100 al-tut", xu, compute_metrics(xu / xu.iloc[0] * base.initial_capital)))

    level = bonferroni_level(tested)
    if eligible is not None:
        scope = (
            f"Evren: geçmiş BIST 100 üyeliği (her gün yalnızca o günkü üyeler), {len(frames)} hisse"
        )
    else:
        scope = f"Evren: BUGÜNKÜ liste, {len(frames)} hisse (survivorship bias içerir; yalnızca karşılaştırma için)"
    lines = [
        f"Dönem: {window[0].date()} – {window[-1].date()} | {scope}",
        f"Komisyon %{base.commission * 100:.2f} + kayma %{base.slippage * 100:.2f} (her yön) | "
        f"nakit: {repr(cash) if cash is not None else 'faizsiz (%0)'}",
    ]
    if skipped:
        lines.append(f"Verisi yetersiz, dışarıda ({len(skipped)}): {', '.join(skipped)}")
        share = len(skipped) / (len(skipped) + len(frames))
        if eligible is not None and share > MAX_MISSING_SHARE:
            lines.append(
                f"⚠️ Eski üyelerin %{share * 100:.0f}'i verisiz: sonuçlar survivorship bias taşır, güvenilir değil. "
                "Önce: python -m core.market.update --bist100-history"
            )
        elif eligible is not None:
            lines.append("  (işlemden kalkmış eski üyelerin verisi yoksa sonuçlar hâlâ biraz iyimserdir)")

    lines += [
        "",
        f"{'Strateji':<42} {'Toplam':>9} {'Yıllık':>8} {'MaxDD':>8} {'Sharpe':>6} {'İşlem':>6}  "
        f"XU100'e göre fazla getiri (yıllık, %{level * 100:.1f} GA)",
    ]
    for i, (name, equity, m) in enumerate(rows):
        stats = (
            bootstrap_excess(excess_returns(equity, bench["close"]), level=level, seed=seed)
            if i < tested
            else None
        )
        test = (
            f"{_pct(stats.mean)} [{_pct(stats.low)}, {_pct(stats.high)}] {stats.verdict}"
            if stats
            else ""
        )
        lines.append(
            f"{name:<42} {_pct(m.get('total_return')):>9} {_pct(m.get('cagr')):>8} "
            f"{_pct(m.get('max_drawdown')):>8} {_num(m.get('sharpe')):>6} {m.get('trades', 0)!s:>6}  {test}"
        )

    lines += [
        "",
        f"GA: blok bootstrap güven aralığı (21 seanslık bloklar). {tested} strateji test edildiği için "
        f"Bonferroni düzeltmeli (%{level * 100:.1f}). Aralık tamamen sıfırın üstünde değilse "
        "strateji XU100'ü geçmiş sayılmaz.",
        "",
        "Walk-forward adımları (24 ay eğitim → 6 ay test):",
    ]
    for s in wf.steps:
        p = s.params
        lines.append(
            f"  {s.test_start.date()} – {s.test_end.date()}: {p['lookback']} gün, "
            f"en iyi {p['top_n']}, rejim {'açık' if p['regime'] else 'kapalı'} "
            f"| eğitim Sharpe {s.train_sharpe:.2f} | test {_pct(s.test_return)} "
            f"| XU100 {_pct(_window_return(bench['close'], s.test_start, s.test_end))}"
        )

    tests = [s.test_return for s in wf.steps]
    if len(tests) > 1:
        excess = [
            s.test_return - _window_return(bench["close"], s.test_start, s.test_end) for s in wf.steps
        ]
        best = max(range(len(tests)), key=tests.__getitem__)
        without_best = float(np.prod([1 + r for i, r in enumerate(tests) if i != best]) - 1)
        lines.append(
            f"  XU100'ü geçen pencere {sum(e > 0 for e in excess)}/{len(excess)} | "
            f"medyan test {_pct(float(np.median(tests)))} | en iyi pencere hariç toplam {_pct(without_best)}"
        )

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="QuantBIST strategy research")
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument("--end", default=None)
    parser.add_argument("--positions", type=int, default=10)
    parser.add_argument("--cash", default=None, help="none | fixed:0.35 | rate:<csv> | fund:<csv>")
    parser.add_argument(
        "--universe", choices=("pit", "today"), default="pit",
        help="pit: point-in-time BIST 100 members (default); today: today's list (survivorship-biased)",
    )
    args = parser.parse_args(argv)

    print(
        research_report(
            start=args.start,
            end=args.end,
            positions=args.positions,
            cash=parse_cash_option(args.cash),
            universe=args.universe,
        )
    )


if __name__ == "__main__":
    main()
