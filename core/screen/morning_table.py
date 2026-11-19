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
MAX_ROWS = 45  # rows per message part (the table goes on in the next message; no row is dropped)
TELEGRAM_LIMIT = 4096  # characters per message, counted here on the HTML text as sent
NOTE_RESERVE = 100  # room for the data line the bot adds under the first message's title (core.market.trust)
BUDGET = TELEGRAM_LIMIT - NOTE_RESERVE
TEXT_CHARS = 200  # a failure or problem line is cut to this many characters before escaping
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

    if _missing(distance_atr):
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
    """(support %, resistance %, nearer distance in ATR) of the nearest cluster levels; None when absent.
    A level without a price is left out before choosing; a NaN distance is never the nearer one."""

    from core.analytics.levels import levels, nearest

    near = nearest([lv for lv in levels(df) if lv.method == "küme" and not _missing(lv.price)], 1)
    sup = near.get("destek") or []
    res = near.get("direnç") or []
    dists = [abs(lv[0].dist_atr) for lv in (sup, res) if lv and not _missing(lv[0].dist_atr)]
    return (sup[0].dist_pct if sup else None, res[0].dist_pct if res else None, min(dists) if dists else None)


def rank(rows: list[Row]) -> list[Row]:
    """Rank 1 = the highest goreli_guc among the rows; rows without a value have no rank and go last."""

    known = sorted((r for r in rows if r.gg is not None and not math.isnan(r.gg)),
                   key=lambda r: (-r.gg, r.symbol))
    for i, r in enumerate(known, 1):
        r.rank = i
    return known + sorted((r for r in rows if r.rank is None), key=lambda r: r.symbol)


def _missing(value) -> bool:
    return value is None or (isinstance(value, (float, int)) and math.isnan(float(value)))


def _pct(value: float | None) -> str:
    return NONE if _missing(value) else f"{value:+.1f}".replace(".", ",")


def short(text: str, n: int = TEXT_CHARS) -> str:
    """A problem or exception line on one line, cut to `n` characters (before escaping)."""

    text = " ".join(str(text).split())
    return text if len(text) <= n else text[: n - 1] + "…"


TOO_LONG = "(bu bölüm Telegram sınırına sığmadı)"
HEAD = ("hisse", "filtre", "GG", "D%/R%", "ATR", "olay", "USD")


def _cells(r: Row, code_of: dict[str, str]) -> tuple[str, ...]:
    try:
        return (r.symbol.removesuffix(".IS"), ",".join(code_of.get(s, s[:4]) for s in r.screens),
                NONE if r.rank is None else str(r.rank),
                f"{_pct(r.support_pct)}/{_pct(r.resistance_pct)}", atr_label(r.distance_atr), r.event, r.usd)
    except Exception:  # noqa: BLE001 - one bad row never stops the table
        return (str(r.symbol).removesuffix(".IS"), NONE, NONE, NONE, NONE, NONE, NONE)


def _lines(rows: list[Row], code_of: dict[str, str]) -> tuple[str, list[str]]:
    body = [_cells(r, code_of) for r in rows]
    widths = [max(len(x[i]) for x in [HEAD, *body]) for i in range(len(HEAD))]
    head, *lines = [" ".join(cell.ljust(w) for cell, w in zip(line, widths)).rstrip() for line in [HEAD, *body]]
    return head, lines


def table_parts(rows: list[Row], code_of: dict[str, str], budget: int = BUDGET,
                max_rows: int = MAX_ROWS) -> list[str]:
    """The monospace table in one or more <pre> blocks (escaped), each with the header line, at most
    `max_rows` rows and at most `budget` characters. Every row is shown and the column widths are the same in
    all parts; a single row too long for the budget is cut."""

    head, lines = _lines(rows, code_of)
    room = budget - len("<pre></pre>") - len(html.escape(head)) - 1
    parts, chunk, size = [], [], 0
    for line in lines:
        text = html.escape(line)
        while len(text) > room and line:
            line = line[:-1]
            text = html.escape(line)
        if chunk and (size + len(text) + 1 > room or len(chunk) >= max_rows):
            parts.append(chunk)
            chunk, size = [], 0
        chunk.append(text)
        size += len(text) + 1
    if chunk:
        parts.append(chunk)
    return ["<pre>" + "\n".join([html.escape(head), *chunk]) + "</pre>" for chunk in parts]


def table(rows: list[Row], code_of: dict[str, str]) -> str:
    """The whole monospace table in one <pre> block (escaped)."""

    head, lines = _lines(rows, code_of)
    return "<pre>" + html.escape("\n".join([head, *lines])) + "</pre>"


def pack(head: list[str], blocks: list[str], cont_head: str, limit: int = BUDGET) -> list[str]:
    """Messages of at most `limit` characters: the first starts with the `head` lines, each next one with
    head[0] (the warning line) and `cont_head`; the blocks follow in order and are never split (a <pre> block
    stays whole). A block longer than a message alone is replaced by a short note (callers keep blocks under
    the budget)."""

    later = "\n".join([head[0], cont_head])
    messages, current = [], "\n".join(head)
    for block in blocks:
        if len(current) + 1 + len(block) > limit:
            messages.append(current)
            current = later
        current += "\n" + (block if len(current) + 1 + len(block) <= limit else TOO_LONG)
    messages.append(current)
    return messages


__all__ = ["BUDGET", "MAX_ROWS", "NOISE", "Row", "TELEGRAM_LIMIT", "WARNING", "atr_label", "codes", "event_flag",
           "nearest_levels", "overlaps", "pack", "rank", "short", "table", "table_parts", "usd_trend"]
