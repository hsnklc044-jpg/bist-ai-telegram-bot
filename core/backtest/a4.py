"""
QuantBIST
a4: the pre-registered hypotheses of docs/RESEARCH_LOG.md ("a4 ön kaydı", 28.10.2026), judged
exactly as fixed there. Nothing here may be tuned after a result is seen.

    python -m core.backtest.a4 [--records history.csv --run-date ...]

H4 holds every BIST 100 member with equal slots; H5 the 10 with the lowest 60-session median
TL turnover. Both rebalance monthly, Aşama 3 engine and costs. Success (all must hold):
- primary: block-bootstrap interval of the excess return over XU100 entirely above zero,
  Bonferroni level for the 2 registered hypotheses (97.5%);
- gate 1: beats XU100 from both starts (2023-08-01 and 2024-01-02);
- gate 2: still beats XU100 without its 5 most profitable stocks;
- gate 3: maximum drawdown not worse than XU100's;
- H5 only: the primary criterion also holds with doubled costs.

Budget rule (docs/RESEARCH_PROGRAM.md): the screening does not run before 27.04.2027; before
that date `run` loads no prices and computes nothing.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from datetime import date

from core.backtest.engine import BacktestConfig, compute_metrics, run_backtest
from core.backtest.reliability import contribution
from core.backtest.research import _universe
from core.backtest.run import load_frames
from core.backtest.stats import bonferroni_level, bootstrap_excess, excess_returns
from core.market.universe import BENCHMARK
from core.strategy.filters import apply_eligibility
from core.strategy.rules import equal_weight_signals, low_turnover_signals

OPEN_DATE = date(2027, 4, 27)
STARTS = ("2023-08-01", "2024-01-02")
HYPOTHESES = 2
TOP_EXCLUDED = 5
COST_MULTIPLIER = 2


@dataclass(frozen=True)
class Rule:
    key: str
    name: str
    positions: int
    signals: object  # (frames, eligible) -> signals
    double_cost_gate: bool


H4 = Rule("H4", "A4-H4 Eşit ağırlık (BIST 100 üyeleri, aylık)", 100, equal_weight_signals, False)
H5 = Rule("H5", "A4-H5 Düşük işlem hacmi (60 seans medyan TL hacim, en düşük 10, aylık)", 10,
          lambda frames, eligible: low_turnover_signals(frames, 60, 10, eligible=eligible), True)


def _pct(x) -> str:
    return "-" if x is None or x != x else f"{x * 100:+.1f}%"


def _signals(rule: Rule, frames, eligible):
    return apply_eligibility(rule.signals(frames, eligible), eligible)


def _xu(bench, equity, capital):
    xu = bench["close"].loc[equity.index[0]: equity.index[-1]]
    return compute_metrics(xu / xu.iloc[0] * capital)


def evaluate(rule: Rule, frames, bench, eligible, seed: int = 0) -> dict:
    config = BacktestConfig(max_positions=rule.positions)
    signals = _signals(rule, frames, eligible)
    runs = {s: run_backtest(frames, signals, config, start=s) for s in STARTS}
    main = runs[STARTS[0]]
    level = bonferroni_level(HYPOTHESES)
    stats = bootstrap_excess(excess_returns(main.equity, bench["close"]), level=level, seed=seed)
    xu = {s: _xu(bench, r.equity, config.initial_capital) for s, r in runs.items()}

    best = list(contribution(main.trades).index[:TOP_EXCLUDED])
    rest = {s: df for s, df in frames.items() if s not in best}
    rest_eligible = eligible[[c for c in eligible.columns if c in rest]]
    without = run_backtest(rest, _signals(rule, rest, rest_eligible), config, start=STARTS[0])

    gates = {
        "primary": stats is not None and stats.low > 0,
        "both_starts": all(runs[s].metrics["cagr"] > xu[s]["cagr"] for s in STARTS),
        "without_best": without.metrics["cagr"] > xu[STARTS[0]]["cagr"],
        "drawdown": main.metrics["max_drawdown"] >= xu[STARTS[0]]["max_drawdown"],
    }
    costly = None
    if rule.double_cost_gate:
        expensive = replace(config, commission=config.commission * COST_MULTIPLIER,
                            slippage=config.slippage * COST_MULTIPLIER)
        costly_run = run_backtest(frames, signals, expensive, start=STARTS[0])
        costly = bootstrap_excess(excess_returns(costly_run.equity, bench["close"]), level=level, seed=seed)
        gates["double_cost"] = costly is not None and costly.low > 0
    return {"rule": rule, "runs": runs, "xu": xu, "stats": stats, "level": level, "best": best,
            "without": without.metrics, "costly": costly, "gates": gates}


def report(result: dict) -> str:
    rule, runs, xu, stats, gates = result["rule"], result["runs"], result["xu"], result["stats"], result["gates"]
    mark = {True: "✓", False: "✗"}
    level = f"%{result['level'] * 100:.1f} GA"
    lines = ["", rule.name]
    for start in STARTS:
        m, x = runs[start].metrics, xu[start]
        lines.append(f"  {start}: yıllık {_pct(m['cagr'])} (XU100 {_pct(x['cagr'])}), MaxDD {_pct(m['max_drawdown'])} "
                     f"(XU100 {_pct(x['max_drawdown'])}), Sharpe {m['sharpe']:.2f}, işlem {m['trades']}")
    lines += [
        f"  XU100'e göre fazla getiri (yıllık, {level}): {_pct(stats.mean)} [{_pct(stats.low)}, {_pct(stats.high)}] "
        f"{stats.verdict}" if stats else f"  XU100'e göre fazla getiri ({level}): veri yetersiz",
        f"  En kârlı {TOP_EXCLUDED} hisse ({', '.join(s.removesuffix('.IS') for s in result['best'])}) olmadan "
        f"yıllık {_pct(result['without'].get('cagr'))}",
    ]
    costly = result["costly"]
    if "double_cost" in gates:
        lines.append(f"  İki kat maliyetle fazla getiri: {_pct(costly.mean)} [{_pct(costly.low)}, {_pct(costly.high)}]"
                     if costly else "  İki kat maliyetle fazla getiri: veri yetersiz")
    lines += [
        "",
        f"  {mark[gates['primary']]} birincil ölçüt (aralık sıfırın üstünde)",
        f"  {mark[gates['both_starts']]} kapı 1: iki başlangıçta da XU100'ün üstünde",
        f"  {mark[gates['without_best']]} kapı 2: en kârlı {TOP_EXCLUDED} hisse olmadan XU100'ün üstünde",
        f"  {mark[gates['drawdown']]} kapı 3: en büyük düşüş XU100'den kötü değil",
    ]
    if "double_cost" in gates:
        lines.append(f"  {mark[gates['double_cost']]} kapı 4: iki kat maliyetle de birincil ölçüt tutuyor")
    lines += ["", "  KARAR: " + ("kabul – holdout'a girer, yalnız canlı ölçüm ve sanal hesap (gerçek para yok)"
                                 if all(gates.values()) else "red – kural ayarlanmaz, sonuç RESEARCH_LOG'a yazılır")]
    return "\n".join(lines)


def records(result: dict) -> list[dict]:
    m, s = result["runs"][STARTS[0]].metrics, result["stats"]
    return [{
        "universe": "a4",
        "period_start": result["runs"][STARTS[0]].equity.index[0].date().isoformat(),
        "period_end": result["runs"][STARTS[0]].equity.index[-1].date().isoformat(),
        "strategy": result["rule"].name, "cagr": m.get("cagr"), "max_drawdown": m.get("max_drawdown"),
        "sharpe": m.get("sharpe"), "trades": m.get("trades", 0), "excess": s.mean if s else None,
        "excess_low": s.low if s else None, "excess_high": s.high if s else None, "level": result["level"],
        "verdict": s.verdict if s else "veri yetersiz",
    }]


def run(today: date, rows: list | None = None) -> str:
    """The screening text; before OPEN_DATE only the reason it did not run."""

    if today < OPEN_DATE:
        return (f"a4 taraması {OPEN_DATE:%d.%m.%Y}'den önce çalıştırılmadı (deneme bütçesi: 6 ayda bir döngü, "
                "docs/RESEARCH_PROGRAM.md). Ön kayıt: docs/RESEARCH_LOG.md \"a4 ön kaydı\".")
    frames, _, eligible = _universe("pit")
    bench = load_frames([BENCHMARK])[BENCHMARK]
    lines = ["a4 – ön kayıtlı hipotezler (docs/RESEARCH_LOG.md \"a4 ön kaydı\").",
             "Evren: geçmiş BIST 100 üyeliği | komisyon %0,10 + kayma %0,05 her yön | Bonferroni 2 hipotez"]
    for rule in (H4, H5):
        result = evaluate(rule, frames, bench, eligible)
        lines.append(report(result))
        if rows is not None:
            rows += records(result)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    from core.infrastructure.console import utf8_output
    from core.market.calendar import now_istanbul

    utf8_output()
    parser = argparse.ArgumentParser(description="a4 pre-registered hypotheses")
    parser.add_argument("--records", default=None, help="append the result to this history CSV")
    parser.add_argument("--run-date", default=None)
    args = parser.parse_args(argv)
    rows: list[dict] = []
    print(run(now_istanbul().date(), rows))
    if args.records and rows:
        from core.backtest.history import append_records

        append_records(rows, args.records, run_date=args.run_date)


if __name__ == "__main__":
    main()


__all__ = ["H4", "H5", "OPEN_DATE", "Rule", "evaluate", "records", "report", "run"]
