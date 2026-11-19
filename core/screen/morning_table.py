"""
QuantBIST
The 09:30 morning table (owner's instruction #15): one message, one table, one row per stock.

Columns: hisse | filtreler (short codes of the subscribed screens it passed) | GG (rank among the rows by
goreli_guc = gg_20, 1 = highest) | D%/R% (nearest cluster support / resistance, % from the last close) |
ATR (the nearer of the two distances in ATR; below 1 ATR "gürültü içinde") | olay (event flag hook, "—"
for now) | USD (see `usd_trend`).

A screen that gives a subset of (or the same list as) another is not a separate list: it only shows as a
code in the filtreler column (`overlaps` names such screens for the owner, who decides which to keep; no
screen definition is changed here). Every field is a display field: a filter record, not a signal.
"""

from __future__ import annotations

import html
import math
import re
from dataclasses import dataclass
from datetime import date

import pandas as pd

WARNING = "Bu filtreler henüz test edilmedi (testler 18.12 sonrası). Filtre sonucudur, karar dayanağı değildir."
NOISE = "gürültü içinde"
NONE = "—"
USD_WINDOW = 200
MAX_ROWS = 45  # keeps the one message inside Telegram's 4096 characters
KNOWN_CODES = {"bist100_aday": "A100", "bist30_aday": "A30", "bist100_trend": "TRD",
               "bist100_geri_cekilme": "GC", "bist100_kirilim": "KRL"}
SUBSET, SAME = "alt küme", "aynı"


def codes(names) -> dict[str, str]:
    """name -> a short (≤ 5 characters) unique code; the live screens have fixed codes."""

    out: dict[str, str] = {}
    for name in sorted(names, key=lambda n: (n not in KNOWN_CODES, n)):
        code = KNOWN_CODES.get(name) or re.sub(r"[^A-Z0-9]", "", name.upper())[:4] or "F"
        base, i = code[:4], 2
        while code in out.values():
            code = f"{base[:3]}{i}"
            i += 1
        out[name] = code
    return out


def overlaps(results: dict[str, set]) -> list[tuple[str, str, str]]:
    """(screen, other, "alt küme" | "aynı") for one morning's lists: `screen` gave a strict subset of
    `other`'s list, or the same list (an identical pair is named once, the later name as the copy). An
    empty list proves nothing and is left out. For the owner's choice only; nothing is removed here."""

    found = []
    names = sorted(n for n, s in results.items() if s)
    for a in names:
        for b in names:
            if a == b:
                continue
            sa, sb = set(results[a]), set(results[b])
            if sa == sb and a > b:
                found.append((a, b, SAME))
            elif sa < sb:
                found.append((a, b, SUBSET))
    return found


def atr_label(distance_atr: float | None) -> str:
    """The nearer level's distance in ATR; under 1 ATR the level is inside the daily noise."""

    if distance_atr is None or (isinstance(distance_atr, float) and math.isnan(distance_atr)):
        return NONE
    if abs(distance_atr) < 1:
        return NOISE
    return f"{abs(distance_atr):.1f}".replace(".", ",")


def usd_trend(close: pd.Series, usdtry: pd.Series) -> str:
    """
    Display field, not a signal. The stock's USD price on a day is its close divided by the TCMB USD/TRY
    rate of the SAME day (days without a rate are left out, never filled). "↑" when the latest USD price
    is above the mean of the last 200 USD prices (latest included), "↓" when below, "—" when the last
    close day has no rate, there are fewer than 200 USD prices, or the two are equal.
    """

    if close is None or usdtry is None or not len(close) or not len(usdtry):
        return NONE
    c = close.dropna().copy()
    r = usdtry.dropna().copy()
    c.index = pd.to_datetime(c.index).normalize()
    r.index = pd.to_datetime(r.index).normalize()
    usd = (c / r.reindex(c.index)).dropna()
    if not len(usd) or usd.index[-1] != c.index[-1] or len(usd) < USD_WINDOW:
        return NONE
    mean = float(usd.iloc[-USD_WINDOW:].mean())
    last = float(usd.iloc[-1])
    return "↑" if last > mean else "↓" if last < mean else NONE


def event_flag(symbol: str, day: date) -> str:
    """Hook for the event flag column (KAP, dividend, split, ...). Not built yet: always "—"."""

    return NONE


@dataclass
class Row:
    symbol: str
    screens: list[str]
    gg: float | None
    support_pct: float | None = None
    resistance_pct: float | None = None
    distance_atr: float | None = None
    usd: str = NONE
    event: str = NONE
    rank: int | None = None


def nearest_levels(df: pd.DataFrame) -> tuple[float | None, float | None, float | None]:
    """(support %, resistance %, nearer distance in ATR) of the nearest cluster levels; None when absent."""

    from core.analytics.levels import levels, nearest

    near = nearest([lv for lv in levels(df) if lv.method == "küme"], 1)
    sup = near.get("destek") or []
    res = near.get("direnç") or []
    dists = [abs(lv[0].dist_atr) for lv in (sup, res) if lv]
    return (sup[0].dist_pct if sup else None, res[0].dist_pct if res else None, min(dists) if dists else None)


def rank(rows: list[Row]) -> list[Row]:
    """Rank 1 = the highest goreli_guc among the rows; rows without a value have no rank and go last."""

    known = sorted((r for r in rows if r.gg is not None and not math.isnan(r.gg)),
                   key=lambda r: (-r.gg, r.symbol))
    for i, r in enumerate(known, 1):
        r.rank = i
    return known + sorted((r for r in rows if r.rank is None), key=lambda r: r.symbol)


def _pct(value: float | None) -> str:
    return NONE if value is None else f"{value:+.1f}".replace(".", ",")


def table(rows: list[Row], code_of: dict[str, str]) -> str:
    """The monospace table (escaped, inside <pre>)."""

    head = ("hisse", "filtre", "GG", "D%/R%", "ATR", "olay", "USD")
    body = []
    for r in rows[:MAX_ROWS]:
        body.append((r.symbol.removesuffix(".IS"), ",".join(code_of[s] for s in r.screens),
                     NONE if r.rank is None else str(r.rank),
                     f"{_pct(r.support_pct)}/{_pct(r.resistance_pct)}", atr_label(r.distance_atr), r.event, r.usd))
    widths = [max(len(x[i]) for x in [head, *body]) for i in range(len(head))]
    lines = [" ".join(cell.ljust(w) for cell, w in zip(line, widths)).rstrip() for line in [head, *body]]
    more = len(rows) - MAX_ROWS
    tail = [f"ve {more} hisse daha"] if more > 0 else []
    return "<pre>" + html.escape("\n".join([*lines, *tail])) + "</pre>"


__all__ = ["MAX_ROWS", "NOISE", "Row", "WARNING", "atr_label", "codes", "event_flag", "nearest_levels",
           "overlaps", "rank", "table", "usd_trend"]
