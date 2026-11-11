"""r1 (K-91; RESEARCH_LOG "r1 ön kaydı"): the rules rejected in a1–a3, unchanged, on 2016-01-04 – 2023-07-31 with the
official data. The research code is not changed: only its price and membership loaders are pointed at the official
frames (core.official.frames). The holdout is never loaded.

    python scripts/r1.py [--db data/official.db] > r1.txt
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

START, END = date(2016, 1, 4), date(2023, 7, 31)
SECOND_START = "2016-06-01"  # the "two start dates" gate, as 2023-08-01 / 2024-01-02 in a3


def main(argv: list[str] | None = None) -> int:
    from core.infrastructure.console import utf8_output

    utf8_output()
    parser = argparse.ArgumentParser(description="r1: reddedilen kurallar, 2016–2023/07 resmî veri")
    parser.add_argument("--db", type=Path, default=None)
    args = parser.parse_args(argv)

    from core.backtest import phase3, research
    from core.market.universe import BENCHMARK
    from core.official import frames as OF

    frames, bench, eligible = OF.load(OF.NEW_SYSTEM_FROM, END, db=args.db)
    frames = {s: df for s, df in frames.items() if len(df) >= 300}  # as the research: a short history stays out
    eligible = eligible[[c for c in eligible.columns if c in frames]]

    research._universe = lambda universe: (frames, [], eligible)
    research.load_frames = lambda symbols, include_holdout=False: {BENCHMARK: bench}
    phase3.load_frames = research.load_frames
    phase3._universe = research._universe
    phase3.STARTS = (START.isoformat(), SECOND_START)

    print(f"r1 · {START} – {END} · resmî veri · {len(frames)} hisse · holdout kapalı\n")
    print("== a1/a2: ana tablo ve aday kurallar (research_report, kod aynen)")
    print(research.research_report(start=START.isoformat(), end=END.isoformat(), universe="pit"))
    print("\n== a3: H1 düşük oynaklık (phase3.evaluate, kod aynen; başlangıçlar 2016-01-04 ve 2016-06-01)")
    print(phase3.report(phase3.evaluate(frames, bench, eligible)))
    try:
        from core.backtest.cash import load_rate_series

        cash = load_rate_series(phase3.POLICY_RATE, phase3.WITHHOLDING)
        strict = load_rate_series(phase3.POLICY_RATE, phase3.WITHHOLDING, spread=phase3.STRICT_SPREAD)
        for rule in (phase3.H2, phase3.H3):
            print(phase3.report_index(phase3.evaluate_index(rule, bench, cash, strict, zero_cash_too=True)))
    except Exception as exc:  # noqa: BLE001 - the pre-registration says: not measurable, never estimated
        print(f"\nH2/H3: ölçülemedi ({type(exc).__name__}: {exc})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
