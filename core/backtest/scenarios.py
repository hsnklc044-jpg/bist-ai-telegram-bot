"""
QuantBIST
Do the data corrections change the research? An isolated experiment.

    python -m core.backtest.scenarios --price-fixes datacheck/latest_price_fixes.csv

Same rules, period, costs and point-in-time universe in four data
scenarios:
    A  original data: corporate actions as before the second-source check
    B  + the corporate actions added from the second-source check (KCAER, CANTE)
    C  A + the one-day close fixes
    D  B + the one-day close fixes
Nothing is written: the price store and data files are only read, and
the overrides are reset at the end.

A better result in a scenario is not evidence that its data is right;
data accuracy is judged by the sources, not by performance.

Also printed: KCAER and CANTE around their dates (stored, corrected and
İş Yatırım closes) and how often a close fix lands outside the day's
stored high/low (the fix then widens the candle: an artificial candle).
"""

from __future__ import annotations

import argparse
import hashlib
from datetime import date
from pathlib import Path

import pandas as pd

from core.backtest.engine import BacktestConfig, run_backtest
from core.backtest.reliability import trade_stats
from core.backtest.research import DEFAULT_START, _universe
from core.market import corrections, store
from core.market.universe import BENCHMARK
from core.strategy.filters import apply_eligibility
from core.strategy.rules import apply_rule, momentum_signals, score_rule, trend_rule

NEW_SOURCE = "datacheck"  # rows added from the second-source check carry this in `source`
SCENARIOS = {"A": (False, False), "B": (True, False), "C": (False, True), "D": (True, True)}
CASES = {
    "KCAER.IS": (date(2024, 11, 20), date(2024, 12, 6)),
    "CANTE.IS": (date(2026, 1, 19), date(2026, 2, 10)),
}


def _pct(x) -> str:
    return "-" if x is None or pd.isna(x) else f"{x * 100:+.1f}%"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def _strategies(frames, eligible, positions):
    gate = (lambda s: apply_eligibility(s, eligible)) if eligible is not None else (lambda s: s)
    return {
        "Bot sinyali": gate(apply_rule(score_rule(70, 70), frames)),
        "Trend kuralı": gate(apply_rule(trend_rule(), frames)),
        f"Momentum 6 ay, en iyi {positions}": momentum_signals(frames, 126, top_n=positions, eligible=eligible),
    }


def run_scenarios(fixes: Path | None, start: str = DEFAULT_START, positions: int = 10) -> dict:
    all_actions = corrections.load_corporate_actions()
    out: dict[str, dict] = {}
    try:
        for name, (with_new, with_fixes) in SCENARIOS.items():
            if with_fixes and fixes is None:
                continue
            corrections.use_corporate_actions(
                all_actions if with_new else [a for a in all_actions if NEW_SOURCE not in (a.source or "")]
            )
            corrections.use_price_fixes(fixes if with_fixes else None)
            frames, _, eligible = _universe("pit")
            config = BacktestConfig(max_positions=positions)
            out[name] = {
                label: run_backtest(frames, signals, config, start=start)
                for label, signals in _strategies(frames, eligible, positions).items()
            }
    finally:
        corrections.use_corporate_actions(None)
        corrections.use_price_fixes(None)
    return out


def format_scenarios(results: dict) -> list[str]:
    lines = []
    strategies = next(iter(results.values())).keys()
    for label in strategies:
        lines += ["", label, f"  {'':3} {'Toplam':>8} {'Yıllık':>8} {'MaxDD':>8} {'Sharpe':>6} {'İşlem':>6} "
                         f"{'Kazanma':>8} {'Beklenti':>9}  A'ya göre işlem farkı"]
        base = {(t.symbol, t.entry_date) for t in results["A"][label].trades}
        for name, by_strategy in results.items():
            res = by_strategy[label]
            m, ts = res.metrics, trade_stats(res.trades)
            keys = {(t.symbol, t.entry_date) for t in res.trades}
            added, removed = keys - base, base - keys
            touched = sorted({s.removesuffix(".IS") for s, _ in added | removed})
            diff = (f"+{len(added)} / −{len(removed)} ({', '.join(touched[:8])}{' …' if len(touched) > 8 else ''})"
                    if added or removed else "aynı")
            lines.append(
                f"  {name:3} {_pct(m.get('total_return')):>8} {_pct(m.get('cagr')):>8} "
                f"{_pct(m.get('max_drawdown')):>8} {m.get('sharpe', float('nan')):>6.2f} {ts.get('trades', 0):>6} "
                f"{_pct(ts.get('win_rate')):>8} {_pct(ts.get('expectancy')):>9}  {diff if name != 'A' else '-'}"
            )
    return lines


def case_studies(get=None) -> list[str]:
    from core.market.crosscheck import fetch_isyatirim

    lines = []
    all_actions = corrections.load_corporate_actions()
    old = [a for a in all_actions if NEW_SOURCE not in (a.source or "")]
    for symbol, (first, last) in CASES.items():
        raw = store.read(symbol)
        stored = raw.loc[pd.Timestamp(first): pd.Timestamp(last), "close"]
        before = corrections.clean(raw, symbol, old).loc[stored.index, "close"]
        after = corrections.clean(raw, symbol, all_actions).loc[stored.index, "close"]
        try:
            theirs = fetch_isyatirim(symbol.removesuffix(".IS"), first, last, get=get)["close"]
        except Exception as exc:  # noqa: BLE001 - shown, never hidden
            theirs = pd.Series(dtype=float)
            lines.append(f"{symbol}: İş Yatırım verisi alınamadı ({exc})")
        table = pd.DataFrame({"depo": stored, "eski düzeltme": before, "yeni düzeltme": after, "İş": theirs})
        returns = table.pct_change()
        lines += ["", f"{symbol.removesuffix('.IS')} {first:%d.%m.%Y} – {last:%d.%m.%Y} (kapanış / günlük getiri)",
                  f"  {'Tarih':10} {'Depo (Yahoo)':>18} {'Eski düzeltme':>18} {'Yeni düzeltme':>18} {'İş Yatırım':>18}"]
        for day, row in table.iterrows():
            cells = [f"{row[c]:9.3f} {_pct(returns.at[day, c]):>7}" if pd.notna(row[c]) else f"{'-':>17}"
                     for c in table.columns]
            lines.append(f"  {day:%d.%m.%Y} " + " ".join(f"{c:>18}" for c in cells))
    return lines


def candle_check(fixes: Path) -> list[str]:
    """How often does a close fix land outside the stored day's high/low?"""

    rows = pd.read_csv(fixes, parse_dates=["date"])
    inside = outside = missing = 0
    stored_outside = 0
    for symbol, part in rows.groupby("symbol"):
        raw = corrections.clean(store.read(symbol), symbol)
        for _, r in part.iterrows():
            if r["date"] not in raw.index:
                missing += 1
                continue
            bar = raw.loc[r["date"]]
            stored_outside += not (bar["low"] - 1e-9 <= bar["close"] <= bar["high"] + 1e-9)
            fixed = bar["close"] * r["factor"]
            if bar["low"] - 1e-9 <= fixed <= bar["high"] + 1e-9:
                inside += 1
            else:
                outside += 1
    total = inside + outside
    return [
        "",
        f"Kapanış düzeltmesi ile mum yapısı ({total} gün, {missing} gün depoda yok):",
        f"  düzeltilmiş kapanış o günün depodaki en düşük–en yüksek aralığında: {inside}",
        f"  aralık dışında (düzeltme mumu genişletir, yapay mum): {outside}",
        f"  depodaki kapanış zaten kendi aralığının dışında: {stored_outside}",
    ]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Research under four data scenarios (A-D).")
    parser.add_argument("--price-fixes", type=Path, default=None)
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument("--positions", type=int, default=10)
    args = parser.parse_args(argv)

    bench = store.read(BENCHMARK)
    actions_file = corrections.CORPORATE_ACTIONS_FILE
    print(f"Veri: fiyat deposu son gün {bench.index[-1].date() if not bench.empty else '-'}; "
          f"corporate_actions.csv sha256 {_sha(actions_file)}"
          + (f"; fiyat düzeltmeleri {args.price_fixes} sha256 {_sha(args.price_fixes)}" if args.price_fixes else ""))
    print(f"Dönem {args.start} – son | geçmiş BIST 100 üyeliği | {args.positions} pozisyon | komisyon+kayma %0,15 her yön")
    print("A orijinal | B + KCAER/CANTE şirket işlemi satırları | C A + tek gün kapanış düzeltmeleri | D B + C")
    print("\n".join(format_scenarios(run_scenarios(args.price_fixes, args.start, args.positions))))
    print("\n".join(case_studies()))
    if args.price_fixes:
        print("\n".join(candle_check(args.price_fixes)))


if __name__ == "__main__":
    main()


__all__ = ["SCENARIOS", "candle_check", "case_studies", "format_scenarios", "run_scenarios"]
