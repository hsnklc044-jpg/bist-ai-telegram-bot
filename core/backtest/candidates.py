"""
QuantBIST
Three-gate test for candidate rules.

    python -m core.backtest.candidates
    python -m core.backtest.candidates --pit        # point-in-time BIST 100 universe

Gate 1: beats XU100 (annual return) from both 2022 and 2023 starts.
Gate 2: still beats XU100 from both starts without its 5 most profitable stocks.
Gate 3: walk-forward (24 months train -> 6 months test, parameters chosen on
        the training window only) beats XU100 over the out-of-sample periods.
The first parameter set of each candidate is its fixed, pre-registered one;
the others exist only for the walk-forward choice.
"""

from __future__ import annotations

import argparse

import pandas as pd

from core.backtest.engine import BacktestConfig, compute_metrics, run_backtest
from core.backtest.reliability import contribution
from core.backtest.walkforward import walk_forward
from core.strategy.candidates import CANDIDATES
from core.strategy.rules import apply_rule

STARTS = ("2022-01-01", "2023-01-01")
WF_START = "2024-01-01"


def _bench_cagr(bench: pd.DataFrame, equity: pd.Series) -> float:
    b = bench["close"].loc[equity.index[0]: equity.index[-1]]
    return compute_metrics(b / b.iloc[0])["cagr"]


def evaluate(name, factory, grid, frames, bench, config, eligibility=None) -> dict:
    def signals(params, fr):
        s = apply_rule(factory(**params), fr)
        if eligibility is not None:
            from core.strategy.filters import apply_eligibility

            s = apply_eligibility(s, eligibility[[c for c in fr if c in eligibility.columns]])
        return s

    out = {"name": name}
    fixed = grid[0]
    gate1 = gate2 = True
    for start in STARTS:
        res = run_backtest(frames, signals(fixed, frames), config, start=start)
        xu = _bench_cagr(bench, res.equity)
        top = list(contribution(res.trades).index[:5])
        rest = {s: df for s, df in frames.items() if s not in top}
        ex = run_backtest(rest, signals(fixed, rest), config, start=start)
        out[start] = {
            "cagr": res.metrics["cagr"], "mdd": res.metrics["max_drawdown"], "trades": res.metrics["trades"],
            "ex5": ex.metrics["cagr"], "xu100": xu,
        }
        gate1 &= res.metrics["cagr"] > xu
        gate2 &= ex.metrics["cagr"] > xu

    wf = walk_forward(frames, lambda p: signals(p, frames), grid, config, start=WF_START, positions_key=None)
    xu_wf = _bench_cagr(bench, wf.equity)
    out["wf"] = {"cagr": wf.metrics.get("cagr"), "xu100": xu_wf,
                 "chosen": [s.params for s in wf.steps]}
    out["gates"] = (gate1, gate2, wf.metrics.get("cagr", float("-inf")) > xu_wf)
    return out


def _pct(x) -> str:
    return "-" if x is None or pd.isna(x) else f"{x * 100:+.1f}%"


def format_results(results: list[dict]) -> str:
    lines = [
        f"{'Aday':<16} {'2022→':>8} {'ilk5 hariç':>10} {'XU100':>7} {'2023→':>8} {'ilk5 hariç':>10} {'XU100':>7} "
        f"{'WF':>7} {'XU100':>7}  Kapılar",
    ]
    for r in results:
        a, b, w = r[STARTS[0]], r[STARTS[1]], r["wf"]
        gates = " ".join("✓" if g else "✗" for g in r["gates"])
        lines.append(
            f"{r['name']:<16} {_pct(a['cagr']):>8} {_pct(a['ex5']):>10} {_pct(a['xu100']):>7} "
            f"{_pct(b['cagr']):>8} {_pct(b['ex5']):>10} {_pct(b['xu100']):>7} {_pct(w['cagr']):>7} {_pct(w['xu100']):>7}  {gates}"
        )
    lines.append("")
    lines.append("Yıllık getiriler. Kapılar: 1 iki başlangıçta XU100'ü geçer; 2 ilk 5 hisse hariç de geçer; "
                 "3 walk-forward test dönemlerinde geçer.")
    for r in results:
        lines.append(f"  {r['name']}: walk-forward seçimleri {r['wf']['chosen']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    from core.backtest.run import load_frames, tradable_symbols
    from core.market.universe import BENCHMARK

    parser = argparse.ArgumentParser(description="QuantBIST candidate rules, three gates")
    parser.add_argument("--positions", type=int, default=10)
    parser.add_argument("--pit", action="store_true", help="point-in-time BIST 100 universe")
    args = parser.parse_args(argv)

    universe, eligibility = None, None
    if args.pit:
        from core.market.membership import ever_members

        universe = ever_members()
    symbols, _ = tradable_symbols(universe)
    frames = {s: df for s, df in load_frames(symbols).items() if not df.empty}
    bench = load_frames([BENCHMARK])[BENCHMARK]
    if args.pit:
        from core.market.membership import membership_panel

        index = pd.DatetimeIndex(sorted(set().union(*(df.index for df in frames.values()))))
        eligibility = membership_panel(index, list(frames))

    config = BacktestConfig(max_positions=args.positions)
    results = [evaluate(n, f, g, frames, bench, config, eligibility) for n, (f, g) in CANDIDATES.items()]
    print(f"{len(frames)} hisse | {args.positions} pozisyon | komisyon+kayma %0,15 her yön | nakit %0\n")
    print(format_results(results))


if __name__ == "__main__":
    main()
