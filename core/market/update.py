"""
QuantBIST
Download / update the local price store.

    python -m core.market.update          # only what is missing
    python -m core.market.update --full   # re-download 5 years
"""

from __future__ import annotations

import argparse
from collections import Counter

from core.market import store
from core.market.data import clear_cache
from core.market.quality import build_report, format_report
from core.market.universe import BENCHMARK, load_universe


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Update the QuantBIST price store.")
    parser.add_argument("--full", action="store_true", help="re-download full history")
    parser.add_argument(
        "--bist100-history",
        action="store_true",
        help="also download every stock that was in BIST 100 since 2022 (needs data/bist100_stable.csv)",
    )
    args = parser.parse_args(argv)

    symbols = [BENCHMARK, *load_universe()]
    if args.bist100_history:
        from core.market.membership import ever_members

        symbols += [s for s in ever_members() if s not in symbols]

    print(f"{len(symbols)} sembol güncelleniyor ({store.HISTORY_YEARS} yıl)...")

    status = store.update(symbols, force=args.full)
    clear_cache()

    counts = Counter(status.values())
    print("Sonuç:", ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))

    failed = [s for s, v in status.items() if v in ("failed", "empty")]
    if failed:
        print("İndirilemeyenler:", ", ".join(failed))

    print()
    print(format_report(build_report([s for s in symbols if s != BENCHMARK])))


if __name__ == "__main__":
    main()
