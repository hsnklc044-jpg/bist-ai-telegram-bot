"""
QuantBIST RC4
Signal Analytics
"""

from __future__ import annotations

from core.analytics.analyzer import analyze_stock


DEFAULT_SYMBOLS = [
    "SASA.IS",
    "SISE.IS",
    "THYAO.IS",
    "TUPRS.IS",
    "ASELS.IS",
    "KCHOL.IS",
    "YKBNK.IS",
    "BIMAS.IS",
    "HEKTS.IS",
    "PETKM.IS",
    "TCELL.IS",
    "GARAN.IS",
    "AKBNK.IS",
    "EREGL.IS",
]


def get_top_signals(
    symbols: list[str] | None = None,
) -> list[dict]:
    """
    Return highest scoring trading opportunities.
    """

    if symbols is None:
        symbols = DEFAULT_SYMBOLS

    opportunities = []

    for symbol in symbols:

        try:

            result = analyze_stock(symbol)

            if not result:
                continue

            if result["signal"] not in (
                "WATCH",
                "BUY",
                "STRONG BUY",
            ):
                continue

            if result["score"] < 50:
                continue

            opportunities.append(result)

        except Exception:
            continue

    opportunities.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return opportunities[:10]