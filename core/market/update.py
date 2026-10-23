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
    args = parser.parse_args(argv)

    symbols = [BENCHMARK, *load_universe()]

    print(f"{len(symbols)} sembol güncelleniyor ({store.HISTORY_YEARS} yıl)...")

    status = store.update(symbols, force=args.full)
    clear_cache()

    counts = Counter(status.values())
    print("Sonuç:", ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))

    failed = [s for s, v in status.items() if v in ("failed", "empty")]
    if failed:
        print("İndirilemeyenler:", ", ".join(failed))

    print()
    print(format_report(build_report()))


if __name__ == "__main__":
    main()
