"""r2 (K-92; RESEARCH_LOG "r2 ön kaydı"): the rules rejected in a1–a3, unchanged, on 2002-01-02 – 2015-11-13 with the
old-system official data, adjusted with the exchange's own factor; the benchmark is the XU100 return index. The research
code is not changed: only its loaders are pointed at the official frames.

    python scripts/r2.py [--db data/official.db] [--inbox data/inbox/bist] > r2.txt
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

WARM_UP, START, END = date(2001, 1, 2), date(2002, 1, 2), date(2015, 11, 13)
SECOND_START = "2002-06-03"


def _cash_covers(path: str, start: date) -> bool:
    """The pre-registration: H2/H3 only when the policy rate series starts on or before the period's start."""

    with open(path, encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(line for line in fh if not line.startswith("#"))]
    first = min(date.fromisoformat(r["effective_date"]) for r in rows)
    return first <= start


def main(argv: list[str] | None = None) -> int:
    from core.infrastructure.console import utf8_output

    utf8_output()
    parser = argparse.ArgumentParser(description="r2: reddedilen kurallar, 2002–2015 eski sistem resmî veri")
    parser.add_argument("--db", type=Path, default=None)
    parser.add_argument("--inbox", type=Path, default=None)
    args = parser.parse_args(argv)

    from core.backtest import phase3, research
    from core.market.universe import BENCHMARK
    from core.official import frames_old as OF

    frames, bench, eligible = OF.load(WARM_UP, END, inbox=args.inbox, db=args.db)
    frames = {s: df for s, df in frames.items() if len(df) >= 300}
    eligible = eligible[[c for c in eligible.columns if c in frames]]

    research._universe = lambda universe: (frames, [], eligible)
    research.load_frames = lambda symbols, include_holdout=False: {BENCHMARK: bench}
    phase3.load_frames = research.load_frames
    phase3._universe = research._universe
    phase3.STARTS = (START.isoformat(), SECOND_START)

    print(f"r2 · {START} – {END} · resmî eski sistem verisi, borsa çarpanıyla düzeltilmiş · ölçüt XU100 getiri endeksi · "
          f"{len(frames)} hisse · holdout kapalı\n")
    print("== a1/a2: ana tablo ve aday kurallar (research_report, kod aynen)")
    print(research.research_report(start=START.isoformat(), end=END.isoformat(), universe="pit"))
    print("\n== a3: H1 düşük oynaklık (phase3.evaluate, kod aynen; başlangıçlar 2002-01-02 ve 2002-06-03)")
    print(phase3.report(phase3.evaluate(frames, bench, eligible)))
    if not _cash_covers(phase3.POLICY_RATE, START):
        print("\nA3-H2 ve A3-H3: ölçülemedi (politika faizi serisi dönemin başını kapsamıyor; ön kayıttaki kural)")
        return 0
    from core.backtest.cash import load_rate_series

    cash = load_rate_series(phase3.POLICY_RATE, phase3.WITHHOLDING)
    strict = load_rate_series(phase3.POLICY_RATE, phase3.WITHHOLDING, spread=phase3.STRICT_SPREAD)
    for rule in (phase3.H2, phase3.H3):
        print(phase3.report_index(phase3.evaluate_index(rule, bench, cash, strict, zero_cash_too=True)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
