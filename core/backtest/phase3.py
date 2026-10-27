"""
QuantBIST
Aşama 3: the pre-registered hypotheses, judged exactly as docs/RESEARCH_LOG.md fixed them.

    python -m core.backtest.phase3 [--records history.csv --run-date ...]

Only H1 (low volatility) is tested: H2 and H3 need cash return data that could not be
obtained under the pre-registered rule (RESEARCH_LOG, 27.10.2026). Nothing here may be tuned
after a result is seen; a failed hypothesis is recorded, not adjusted.

Success (all must hold):
- primary: the block-bootstrap interval of the excess return over XU100 is entirely above
  zero, Bonferroni level for the 3 registered hypotheses;
- gate 1: beats XU100 from both starts (2023-08-01 and 2024-01-02);
- gate 2: still beats XU100 without its 5 most profitable stocks;
- gate 3: its maximum drawdown is not worse than XU100's.
"""

from __future__ import annotations

import argparse

from core.backtest.engine import BacktestConfig, compute_metrics, run_backtest
from core.backtest.reliability import contribution
from core.backtest.research import _universe
from core.backtest.run import load_frames
from core.backtest.stats import bonferroni_level, bootstrap_excess, excess_returns
from core.market.universe import BENCHMARK
from core.strategy.filters import apply_eligibility
from core.strategy.rules import low_volatility_signals

STARTS = ("2023-08-01", "2024-01-02")
HYPOTHESES = 3  # registered; Bonferroni level is for all three
POSITIONS = 10
WINDOW = 60
TOP_EXCLUDED = 5
NAME = "A3-H1 Düşük oynaklık (60 seans, en sakin 10, aylık)"


def _pct(x) -> str:
    return "-" if x is None or x != x else f"{x * 100:+.1f}%"


def _signals(frames, eligible):
    return apply_eligibility(low_volatility_signals(frames, WINDOW, POSITIONS, eligible=eligible), eligible)


def _xu(bench, equity, capital):
    xu = bench["close"].loc[equity.index[0]: equity.index[-1]]
    return compute_metrics(xu / xu.iloc[0] * capital)


def evaluate(frames, bench, eligible, seed: int = 0) -> dict:
    config = BacktestConfig(max_positions=POSITIONS)
    runs = {s: run_backtest(frames, _signals(frames, eligible), config, start=s) for s in STARTS}
    main = runs[STARTS[0]]
    level = bonferroni_level(HYPOTHESES)
    stats = bootstrap_excess(excess_returns(main.equity, bench["close"]), level=level, seed=seed)
    xu = {s: _xu(bench, r.equity, config.initial_capital) for s, r in runs.items()}

    best = list(contribution(main.trades).index[:TOP_EXCLUDED])
    rest = {s: df for s, df in frames.items() if s not in best}
    rest_eligible = eligible[[c for c in eligible.columns if c in rest]]
    without = run_backtest(rest, _signals(rest, rest_eligible), config, start=STARTS[0])

    gates = {
        "primary": stats is not None and stats.low > 0,
        "both_starts": all(runs[s].metrics["cagr"] > xu[s]["cagr"] for s in STARTS),
        "without_best": without.metrics["cagr"] > xu[STARTS[0]]["cagr"],
        "drawdown": main.metrics["max_drawdown"] >= xu[STARTS[0]]["max_drawdown"],
    }
    return {"runs": runs, "xu": xu, "stats": stats, "level": level, "best": best,
            "without": without.metrics, "gates": gates}


def report(result: dict) -> str:
    runs, xu, stats, gates = result["runs"], result["xu"], result["stats"], result["gates"]
    mark = {True: "✓", False: "✗"}
    lines = [
        "Aşama 3 – ön kayıtlı hipotezler (docs/RESEARCH_LOG.md). H2 ve H3 test edilmiyor: nakit verisi yok.",
        f"Evren: geçmiş BIST 100 üyeliği | {POSITIONS} pozisyon | komisyon %0,10 + kayma %0,05 her yön",
        "",
        NAME,
    ]
    for start in STARTS:
        m, x = runs[start].metrics, xu[start]
        lines.append(f"  {start}: yıllık {_pct(m['cagr'])} (XU100 {_pct(x['cagr'])}), MaxDD {_pct(m['max_drawdown'])} "
                     f"(XU100 {_pct(x['max_drawdown'])}), Sharpe {m['sharpe']:.2f}, işlem {m['trades']}")
    level = f"%{result['level'] * 100:.1f} GA"
    lines += [
        f"  XU100'e göre fazla getiri (yıllık, {level}): {_pct(stats.mean)} [{_pct(stats.low)}, {_pct(stats.high)}] "
        f"{stats.verdict}" if stats else f"  XU100'e göre fazla getiri ({level}): veri yetersiz",
        f"  En kârlı {TOP_EXCLUDED} hisse ({', '.join(s.removesuffix('.IS') for s in result['best'])}) olmadan "
        f"yıllık {_pct(result['without'].get('cagr'))}",
        "",
        f"  {mark[gates['primary']]} birincil ölçüt (aralık sıfırın üstünde)",
        f"  {mark[gates['both_starts']]} kapı 1: iki başlangıçta da XU100'ün üstünde",
        f"  {mark[gates['without_best']]} kapı 2: en kârlı {TOP_EXCLUDED} hisse olmadan XU100'ün üstünde",
        f"  {mark[gates['drawdown']]} kapı 3: en büyük düşüş XU100'den kötü değil",
        "",
        "  KARAR: " + ("kabul – yalnız canlı ölçüme alınır (gerçek para yok)" if all(gates.values())
                       else "red – kural ayarlanmaz, sonuç RESEARCH_LOG'a yazılır"),
    ]
    return "\n".join(lines)


def records(result: dict) -> list[dict]:
    m, s = result["runs"][STARTS[0]].metrics, result["stats"]
    return [{
        "universe": "a3",
        "period_start": result["runs"][STARTS[0]].equity.index[0].date().isoformat(),
        "period_end": result["runs"][STARTS[0]].equity.index[-1].date().isoformat(),
        "strategy": NAME, "cagr": m.get("cagr"), "max_drawdown": m.get("max_drawdown"), "sharpe": m.get("sharpe"),
        "trades": m.get("trades", 0), "excess": s.mean if s else None, "excess_low": s.low if s else None,
        "excess_high": s.high if s else None, "level": result["level"], "verdict": s.verdict if s else "veri yetersiz",
    }]


def main(argv: list[str] | None = None) -> None:
    from core.infrastructure.console import utf8_output

    utf8_output()
    parser = argparse.ArgumentParser(description="Aşama 3 pre-registered hypotheses")
    parser.add_argument("--records", default=None, help="append the result to this history CSV")
    parser.add_argument("--run-date", default=None)
    args = parser.parse_args(argv)

    frames, _, eligible = _universe("pit")
    bench = load_frames([BENCHMARK])[BENCHMARK]
    result = evaluate(frames, bench, eligible)
    print(report(result))
    if args.records:
        from core.backtest.history import append_records

        append_records(records(result), args.records, run_date=args.run_date)


if __name__ == "__main__":
    main()


__all__ = ["evaluate", "records", "report"]
