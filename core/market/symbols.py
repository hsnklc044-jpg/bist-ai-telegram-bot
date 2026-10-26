"""
QuantBIST
BIST ticker normalisation (no heavy imports, safe to use anywhere).
"""

from __future__ import annotations

import re

_SYMBOL_PATTERN = re.compile(r"^[A-Z0-9]{2,10}$")


def normalize_symbol(symbol: str) -> str:
    """
    Convert user input into a Yahoo Finance BIST ticker.

    "eregl" -> "EREGL.IS", "THYAO.IS" -> "THYAO.IS"
    """

    code = str(symbol).strip().upper().removesuffix(".IS")

    if not _SYMBOL_PATTERN.match(code):
        raise ValueError(f"Geçersiz hisse kodu: {symbol!r}")

    return f"{code}.IS"


__all__ = ["normalize_symbol"]
