"""
QuantBIST
Aşama 3: the pre-registered hypotheses, judged exactly as docs/RESEARCH_LOG.md fixed them.

    python -m core.backtest.phase3 [--records history.csv --run-date ...]

H1 (low volatility) holds stocks. H2 (index trend) and H3 (turn of the month) hold XU100 or
cash; under plan change 1 (RESEARCH_LOG, 27.10.2026) cash earns the TCMB policy rate net of
withholding tax, and the verdict must also hold at the policy rate minus 3 points. Nothing
here may be tuned after a result is seen; a failed hypothesis is recorded, not adjusted.

Success (all must hold):
- primary: the block-bootstrap interval of the excess return over XU100 is entirely above
  zero, Bonferroni level for the 3 registered hypotheses;
- gate 1: beats XU100 from both starts (2023-08-01 and 2024-01-02);
- gate 2: H1 still beats XU100 without its 5 most profitable stocks; H2/H3 beat XU100 in at
  least 3 of the 4 calendar years 2023–2026;
- gate 3: its maximum drawdown is not worse than XU100's.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from core.backtest.engine import BacktestConfig, compute_metrics, run_backtest
from core.backtest.reliability import contribution, yearly_returns
from core.backtest.research import _universe
from core.backtest.run import load_frames
from core.backtest.stats import bonferroni_level, bootstrap_excess, excess_returns
from core.market.universe import BENCHMARK
from core.strategy.filters import apply_eligibility
from core.strategy.rules import index_trend_signals, low_volatility_signals, turn_of_month_signals

STARTS = ("2023-08-01", "2024-01-02")
HYPOTHESES = 3  # registered; Bonferroni level is for all three
POSITIONS = 10
WINDOW = 60
TOP_EXCLUDED = 5
NAME = "A3-H1 Düşük oynaklık (60 seans, en sakin 10, aylık)"
POLICY_RATE = "data/cash/policy_rate.csv"
WITHHOLDING = "data/cash/withholding.csv"
STRICT_SPREAD = 0.03  # plan change 1: the verdict must also hold 3 points below the policy rate
MIN_WINNING_YEARS = 3


@dataclass(frozen=True)
class IndexRule:
    name: str
    signals: object  # benchmark frame -> enter / exit / rank frame


H2 = IndexRule("A3-H2 Endeks trendi (XU100 > 200 seans ort., aylık; değilse nakit)", lambda b: index_trend_signals(b, 200))
H3 = IndexRule("A3-H3 Ay dönümü (son 3 + ilk 3 seans XU100; değilse nakit)", lambda b: turn_of_month_signals(b, 3))


def _pct(x) -> str:
    return "-" if x is None or x != x else f"{x * 100:+.1f}%"


def _signals(frames, eligible):
    return apply_eligibility(low_volatility_signals(frames, WINDOW, POSITIONS, eligible=eligible), eligible)


def _xu_curve(bench, equity, capital):
    xu = bench["close"].loc[equity.index[0]: equity.index[-1]]
    return xu / xu.iloc[0] * capital


def _xu(bench, equity, capital):
    return compute_metrics(_xu_curve(bench, equity, capital))


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
        "Aşama 3 – ön kayıtlı hipotezler (docs/RESEARCH_LOG.md; H2/H3 nakdi: plan değişikliği 1).",
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


def _judge_index(rule: IndexRule, bench, cash, seed: int) -> dict:
    frames = {BENCHMARK: bench}
    signals = {BENCHMARK: rule.signals(bench)}
    config = BacktestConfig(max_positions=1, cash=cash)
    runs = {s: run_backtest(frames, signals, config, start=s) for s in STARTS}
    main = runs[STARTS[0]]
    stats = bootstrap_excess(excess_returns(main.equity, bench["close"]), level=bonferroni_level(HYPOTHESES), seed=seed)
    xu = {s: _xu(bench, r.equity, config.initial_capital) for s, r in runs.items()}
    ours = yearly_returns(main.equity)
    theirs = yearly_returns(_xu_curve(bench, main.equity, config.initial_capital))
    wins = int(sum(ours[y] > theirs[y] for y in ours.index if y in theirs.index))
    gates = {
        "primary": stats is not None and stats.low > 0,
        "both_starts": all(runs[s].metrics["cagr"] > xu[s]["cagr"] for s in STARTS),
        "years": wins >= MIN_WINNING_YEARS,
        "drawdown": main.metrics["max_drawdown"] >= xu[STARTS[0]]["max_drawdown"],
    }
    return {"runs": runs, "xu": xu, "stats": stats, "gates": gates, "years": (wins, len(ours))}


def evaluate_index(rule: IndexRule, bench, cash, strict_cash, zero_cash_too: bool = False, seed: int = 0) -> dict:
    """H2/H3: judged with the policy-rate cash, and again with the stricter cash (both must pass).
    With zero_cash_too, also run with 0% cash, for information only."""

    main = _judge_index(rule, bench, cash, seed)
    strict = _judge_index(rule, bench, strict_cash, seed)
    zero = _judge_index(rule, bench, None, seed) if zero_cash_too else None
    return {**main, "rule": rule, "level": bonferroni_level(HYPOTHESES), "strict": strict,
            "strict_gates": strict["gates"], "zero": zero}


def _index_lines(label: str, part: dict) -> list[str]:
    lines = [f"  [{label}]"]
    for start in STARTS:
        m, x = part["runs"][start].metrics, part["xu"][start]
        lines.append(f"    {start}: yıllık {_pct(m['cagr'])} (XU100 {_pct(x['cagr'])}), MaxDD {_pct(m['max_drawdown'])} "
                     f"(XU100 {_pct(x['max_drawdown'])}), Sharpe {m['sharpe']:.2f}, işlem {m['trades']}, "
                     f"piyasada %{m.get('exposure', 0.0) * 100:.0f}")
    stats = part["stats"]
    lines.append(f"    fazla getiri: {_pct(stats.mean)} [{_pct(stats.low)}, {_pct(stats.high)}] {stats.verdict}"
                 if stats else "    fazla getiri: veri yetersiz")
    lines.append(f"    XU100'ün üstünde kalınan takvim yılı: {part['years'][0]}/{part['years'][1]}")
    return lines


def report_index(result: dict) -> str:
    mark = {True: "✓", False: "✗"}
    names = {"primary": "birincil ölçüt (aralık sıfırın üstünde)", "both_starts": "kapı 1: iki başlangıçta da XU100'ün üstünde",
             "years": f"kapı 2: en az {MIN_WINNING_YEARS} takvim yılında XU100'ün üstünde",
             "drawdown": "kapı 3: en büyük düşüş XU100'den kötü değil"}
    lines = ["", result["rule"].name,
             f"  Fazla getiri aralığı yıllık, %{result['level'] * 100:.1f} GA (Bonferroni, 3 hipotez)"]
    lines += _index_lines("nakit: politika faizi, stopajlı", result)
    lines += _index_lines("nakit: politika faizi − 3 puan, stopajlı", result["strict"])
    if result["zero"] is not None:
        z = result["zero"]["runs"][STARTS[0]].metrics
        lines.append(f"  [bilgi: nakit %0] {STARTS[0]}: yıllık {_pct(z['cagr'])}, MaxDD {_pct(z['max_drawdown'])}")
    lines.append("")
    for key, text in names.items():
        lines.append(f"  {mark[result['gates'][key]]}/{mark[result['strict_gates'][key]]} {text}  (politika / −3 puan)")
    accepted = all(result["gates"].values()) and all(result["strict_gates"].values())
    lines += ["", "  KARAR: " + ("kabul – yalnız canlı ölçüme alınır (gerçek para yok)" if accepted
                                 else "red – kural ayarlanmaz, sonuç RESEARCH_LOG'a yazılır")]
    return "\n".join(lines)


def index_records(result: dict) -> list[dict]:
    rows = []
    for part, suffix in ((result, ""), (result["strict"], " [nakit −3 puan]")):
        m, s = part["runs"][STARTS[0]].metrics, part["stats"]
        rows.append({
            "universe": "a3",
            "period_start": part["runs"][STARTS[0]].equity.index[0].date().isoformat(),
            "period_end": part["runs"][STARTS[0]].equity.index[-1].date().isoformat(),
            "strategy": result["rule"].name + suffix, "cagr": m.get("cagr"), "max_drawdown": m.get("max_drawdown"),
            "sharpe": m.get("sharpe"), "trades": m.get("trades", 0), "excess": s.mean if s else None,
            "excess_low": s.low if s else None, "excess_high": s.high if s else None, "level": result["level"],
            "verdict": s.verdict if s else "veri yetersiz",
        })
    return rows


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

    from core.backtest.cash import load_rate_series

    frames, _, eligible = _universe("pit")
    bench = load_frames([BENCHMARK])[BENCHMARK]
    result = evaluate(frames, bench, eligible)
    rows = records(result)
    print(report(result))
    cash = load_rate_series(POLICY_RATE, WITHHOLDING)
    strict = load_rate_series(POLICY_RATE, WITHHOLDING, spread=STRICT_SPREAD)
    for rule in (H2, H3):
        index_result = evaluate_index(rule, bench, cash, strict, zero_cash_too=True)
        print(report_index(index_result))
        rows += index_records(index_result)
    if args.records:
        from core.backtest.history import append_records

        append_records(rows, args.records, run_date=args.run_date)


if __name__ == "__main__":
    main()


__all__ = ["H2", "H3", "IndexRule", "evaluate", "evaluate_index", "index_records", "records", "report", "report_index"]
