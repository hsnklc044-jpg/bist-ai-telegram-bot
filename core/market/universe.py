"""
QuantBIST
Stock universe.

The list of stocks the system scans and uses for market breadth lives
in data/universe.csv (columns: symbol, name). Add rows to widen the
scan; codes may be written with or without the .IS suffix.
"""

from __future__ import annotations

import csv

from core.config.paths import UNIVERSE_FILE
from core.infrastructure.logger import get_logger

logger = get_logger(__name__)

BENCHMARK = "XU100.IS"

FALLBACK = (
    "AKBNK.IS", "ASELS.IS", "BIMAS.IS", "EREGL.IS", "GARAN.IS",
    "HEKTS.IS", "KCHOL.IS", "PETKM.IS", "SASA.IS", "SISE.IS",
    "TCELL.IS", "THYAO.IS", "TUPRS.IS", "YKBNK.IS",
)


def _ticker(code: str) -> str:
    code = code.strip().upper().removesuffix(".IS")
    return f"{code}.IS"


def load_universe() -> list[str]:
    """Symbols from data/universe.csv, in file order, without duplicates."""

    try:
        with open(UNIVERSE_FILE, encoding="utf-8-sig", newline="") as fh:
            rows = csv.DictReader(fh)
            symbols = [_ticker(r["symbol"]) for r in rows if r.get("symbol", "").strip()]
    except FileNotFoundError:
        logger.warning("Universe file missing, using built-in list: %s", UNIVERSE_FILE)
        return list(FALLBACK)

    return list(dict.fromkeys(symbols)) or list(FALLBACK)


__all__ = [
    "BENCHMARK",
    "load_universe",
]
