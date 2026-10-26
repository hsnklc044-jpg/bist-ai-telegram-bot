"""
QuantBIST
Reliability report: how much of a backtest result survives scrutiny.

    python -m core.backtest.reliability --rule trend_filtered
    python -m core.backtest.reliability --rule trend --start 2022-01-01 --cash fixed:0.35
    python -m core.backtest.reliability --rule momentum --volume-cap 0.01 --capital 1000000

For one rule it reports, next to the plain result:
- per-trade statistics: expectancy, win rate, payoff ratio, profit factor
- year-by-year returns against XU100
- returns split by market regime (rising / falling / sideways XU100)
- profit contribution per stock, and the result WITHOUT the top 5 stocks
- the result with 2x and 3x commission and slippage
- the result with purchases capped at a share of daily turnover

A rule whose edge disappears in any of these lines is not a signal.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import replace

import numpy as np
import pandas as pd

from core.backtest.cash import parse_cash_option
from core.backtest.engine import (
    BacktestConfig,
    BacktestResult,
    Trade,
    compute_metrics,
    run_backtest,
)

TOP_N = 5
REGIME_WINDOW = 63
REGIME_BAND = 0.05

# ---------------------------------------------------------------------------
# Pure functions (tested on small hand-computed cases)
# ---------------------------------------------------------------------------


def trade_stats(trades: list[Trade]) -> dict:
    """Per-trade statistics on net returns (entry and exit prices include costs)."""

    rets = np.array([t.gross_return for t in trades], dtype=float)
    if not len(rets):
        return {"trades": 0}
    wins, losses = rets[rets > 0], rets[rets <= 0]
    avg_win = float(wins.mean()) if len(wins) else float("nan")
    avg_loss = float(losses.mean()) if len(losses) else float("nan")
    profit = sum(t.shares * (t.exit_price - t.entry_price) for t in trades if t.gross_return > 0)
    loss = -sum(t.shares * (t.exit_price - t.entry_price) for t in trades if t.gross_return <= 0)
    return {
        "trades": int(len(rets)),
        "expectancy": float(rets.mean()),
        "win_rate": float(len(wins) / len(rets)),
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "payoff_ratio": avg_win / abs(avg_loss) if len(wins) and len(losses) and avg_loss else float("nan"),
        "profit_factor": profit / loss if loss else float("nan"),
    }


def yearly_returns(equity: pd.Series) -> pd.Series:
    """Calendar-year returns; the first year runs from the first value."""

    year_end = equity.groupby(equity.index.year).last()
    previous = year_end.shift(1)
    previous.iloc[0] = equity.iloc[0]
    return year_end / previous - 1


def market_regime(benchmark_close: pd.Series, window: int = REGIME_WINDOW, band: float = REGIME_BAND) -> pd.Series:
    """
    Label each day by the benchmark's trailing `window`-day return, known
    at that day's close: 'yükselen' above +band, 'düşen' below -band,
    otherwise 'yatay'. NaN while there is not enough history.
    """

    change = benchmark_close / benchmark_close.shift(window) - 1
    label = pd.Series(np.where(change > band, "yükselen", np.where(change < -band, "düşen", "yatay")), index=benchmark_close.index)
    return label.where(change.notna())


def regime_breakdown(equity: pd.Series, regime: pd.Series) -> pd.DataFrame:
    """
    Strategy returns grouped by the regime label of the PREVIOUS close
    (the label known when the day's position was held).
    """

    daily = equity.pct_change().dropna()
    label = regime.reindex(equity.index).shift(1).reindex(daily.index)
    rows = {}
    for name in ("yükselen", "yatay", "düşen"):
        r = daily[label == name]
        if r.empty:
            continue
        growth = float((1 + r).prod())
        rows[name] = {
            "days": int(len(r)),
            "total": growth - 1,
            "annualized": growth ** (252 / len(r)) - 1,
        }
    return pd.DataFrame(rows).T


def contribution(trades: list[Trade]) -> pd.Series:
    """Profit in currency per symbol (net of costs), largest first."""

    pnl: dict[str, float] = {}
    for t in trades:
        pnl[t.symbol] = pnl.get(t.symbol, 0.0) + t.shares * (t.exit_price - t.entry_price)
    return pd.Series(pnl, dtype=float).sort_values(ascending=False)


# ---------------------------------------------------------------------------
# The report
# ---------------------------------------------------------------------------


def _pct(x) -> str:
    return "-" if x is None or pd.isna(x) else f"{x * 100:+.1f}%"


def _share(x) -> str:
    return "-" if x is None or pd.isna(x) else f"%{x * 100:.0f}"


def _num(x) -> str:
    return "-" if x is None or pd.isna(x) else f"{x:.2f}"


def reliability_report(
    frames: dict[str, pd.DataFrame],
    build_signals: Callable[[dict[str, pd.DataFrame]], object],
    config: BacktestConfig,
    benchmark: pd.DataFrame,
    start=None,
    end=None,
    name: str = "strateji",
    volume_cap: float = 0.01,
) -> str:
    def run(fr, cfg) -> BacktestResult:
        return run_backtest(fr, build_signals(fr), cfg, start=start, end=end)

    base = run(frames, config)
    eq = base.equity
    bench = benchmark["close"].loc[eq.index[0]: eq.index[-1]]
    bench_curve = bench / bench.iloc[0] * config.initial_capital
    m, b = base.metrics, compute_metrics(bench_curve)

    lines = [
        f"Güvenilirlik raporu: {name}",
        f"Dönem {m['start']} – {m['end']} | {len(frames)} hisse | {config.max_positions} pozisyon | "
        f"sermaye {config.initial_capital:,.0f} TL",
        f"Maliyet: komisyon %{config.commission * 100:.2f} + kayma %{config.slippage * 100:.2f} (her yön) | "
        f"nakit: {m.get('cash_model', 'faizsiz (%0)')}",
    ]
    if m.get("cash_missing_days"):
        lines.append(f"UYARI: nakit verisi eksik gün sayısı {m['cash_missing_days']} (bu günler faizsiz sayıldı)")

    def row(label, mm):
        return (
            f"{label:<34} {_pct(mm.get('total_return')):>9} {_pct(mm.get('cagr')):>8} "
            f"{_pct(mm.get('max_drawdown')):>8} {_num(mm.get('sharpe')):>6} {mm.get('trades', 0)!s:>6}"
        )

    header = f"{'':<34} {'Toplam':>9} {'Yıllık':>8} {'MaxDD':>8} {'Sharpe':>6} {'İşlem':>6}"

    # 1. Plain result, top-5 removed, costs, liquidity
    contrib = contribution(base.trades)
    top = list(contrib.index[:TOP_N])
    without_top = run({s: df for s, df in frames.items() if s not in top}, config)
    cost2 = run(frames, replace(config, commission=config.commission * 2, slippage=config.slippage * 2))
    cost3 = run(frames, replace(config, commission=config.commission * 3, slippage=config.slippage * 3))
    capped = run(frames, replace(config, max_volume_share=volume_cap))

    lines += [
        "",
        header,
        row(name, m),
        row(f"  ilk {TOP_N} hisse hariç", without_top.metrics),
        row("  2 kat maliyet", cost2.metrics),
        row("  3 kat maliyet", cost3.metrics),
        row(f"  alım ≤ günlük işlem hacminin %{volume_cap * 100:g}'i", capped.metrics),
        row("XU100 al-tut", b),
        "",
        f"Çıkarılan ilk {TOP_N}: " + ", ".join(f"{s} ({v:,.0f} TL)" for s, v in contrib.head(TOP_N).items()),
    ]
    total_pnl = contrib.sum()
    if total_pnl:
        lines.append(f"İlk {TOP_N} hissenin toplam kâra payı: {_share(contrib.head(TOP_N).sum() / total_pnl)}")

    # 2. Per-trade statistics
    st = trade_stats(base.trades)
    lines += [
        "",
        "İşlem başına:",
        f"  beklenti {_pct(st.get('expectancy'))} | kazanma oranı {_share(st.get('win_rate'))} | "
        f"ort. kazanç {_pct(st.get('avg_win'))} | ort. kayıp {_pct(st.get('avg_loss'))} | "
        f"kazanç/kayıp oranı {_num(st.get('payoff_ratio'))} | kâr faktörü {_num(st.get('profit_factor'))}",
    ]

    # 3. Year by year
    years = pd.DataFrame({name: yearly_returns(eq), "XU100": yearly_returns(bench_curve)})
    lines += ["", "Yıllara göre:", f"  {'Yıl':<6} {name[:20]:>20} {'XU100':>9} {'Fark':>9}"]
    for year, r in years.iterrows():
        lines.append(f"  {year:<6} {_pct(r[name]):>20} {_pct(r['XU100']):>9} {_pct(r[name] - r['XU100']):>9}")

    # 4. Market regime
    regimes = regime_breakdown(eq, market_regime(benchmark["close"]))
    bench_regimes = regime_breakdown(bench_curve, market_regime(benchmark["close"]))
    lines += [
        "",
        f"Piyasa rejimine göre (XU100'ün son {REGIME_WINDOW} günlük getirisi, ±%{REGIME_BAND * 100:g} bant):",
        f"  {'Rejim':<10} {'Gün':>5} {name[:20]:>20} {'XU100':>9}  (yıllıklandırılmış)",
    ]
    for regime_name, r in regimes.iterrows():
        xb = bench_regimes.loc[regime_name, "annualized"] if regime_name in bench_regimes.index else np.nan
        lines.append(f"  {regime_name:<10} {int(r['days']):>5} {_pct(r['annualized']):>20} {_pct(xb):>9}")

    return "\n".join(lines)


RULES = ("trend", "trend_filtered", "score", "momentum")


def _builder(rule: str, regime: pd.Series):
    from core.strategy.filters import apply_eligibility, eligibility
    from core.strategy.rules import (
        apply_rule,
        momentum_signals,
        score_rule,
        trend_rule,
        with_regime,
    )

    if rule == "trend":
        return lambda fr: apply_rule(trend_rule(), fr)
    if rule == "trend_filtered":
        return lambda fr: apply_eligibility(
            apply_rule(trend_rule(), fr),
            eligibility(fr, liquidity_top=50, max_run_up=1.0),
            exit_when_ineligible=True,
        )
    if rule == "score":
        return lambda fr: with_regime(apply_rule(score_rule(70, 70), fr), regime)
    if rule == "momentum":
        return lambda fr: momentum_signals(fr, 126, top_n=10, regime=regime)
    raise ValueError(rule)


def main(argv: list[str] | None = None) -> None:
    from core.backtest.run import load_frames, tradable_symbols
    from core.market.universe import BENCHMARK
    from core.strategy.rules import regime_filter

    parser = argparse.ArgumentParser(description="QuantBIST reliability report")
    parser.add_argument("--rule", choices=RULES, default="trend_filtered")
    parser.add_argument("--start", default="2022-01-01")
    parser.add_argument("--end", default=None)
    parser.add_argument("--positions", type=int, default=10)
    parser.add_argument("--capital", type=float, default=100_000.0)
    parser.add_argument("--cash", default=None, help="none | fixed:0.35 | rate:<csv>[,tax=..] | fund:<csv>[,tax=..]")
    parser.add_argument("--volume-cap", type=float, default=0.01)
    parser.add_argument(
        "--pit",
        action="store_true",
        help="point-in-time BIST 100: stocks that were in the index on each date (survivorship control)",
    )
    args = parser.parse_args(argv)

    universe = None
    if args.pit:
        from core.market.membership import ever_members

        universe = ever_members()
    symbols, skipped = tradable_symbols(universe)
    frames = {s: df for s, df in load_frames(symbols).items() if not df.empty}
    bench = load_frames([BENCHMARK])[BENCHMARK]
    builder = _builder(args.rule, regime_filter(bench))
    if args.pit:
        from core.market.membership import membership_panel
        from core.strategy.filters import apply_eligibility

        index = pd.DatetimeIndex(sorted(set().union(*(df.index for df in frames.values()))))
        panel = membership_panel(index, list(frames))
        base_builder = builder

        def builder(fr):
            return apply_eligibility(base_builder(fr), panel[[s for s in fr if s in panel.columns]])

        print(
            f"Evren: her tarihte o günkü BIST 100 üyeleri ({len(frames)} hisse verili; "
            f"verisi olmayan ya da sorunlu {len(skipped)}: {', '.join(skipped[:15])}{' ...' if len(skipped) > 15 else ''})\n"
        )
    config = BacktestConfig(
        initial_capital=args.capital,
        max_positions=args.positions,
        cash=parse_cash_option(args.cash),
    )
    print(
        reliability_report(
            frames,
            builder,
            config,
            bench,
            start=args.start,
            end=args.end,
            name=args.rule,
            volume_cap=args.volume_cap,
        )
    )


if __name__ == "__main__":
    main()


__all__ = [
    "trade_stats",
    "yearly_returns",
    "market_regime",
    "regime_breakdown",
    "contribution",
    "reliability_report",
]
