"""Data trust levels (J, the user's 11.11.2026 decision; docs/DATA_SOURCES.md "Güven seviyeleri").

Level 1: official or licensed source (Borsa İstanbul, KAP, a licensed vendor, a broker API).
Level 2: unofficial, but checked against an independent second source.
Level 3: unofficial and unchecked. Yahoo prices are level 3 until a second-source check passes.

A score, screen or filter carries the level of the weakest data it uses (`weakest`). A Telegram message built on
level 3 data gets one short line under its title (`with_note`); a research decision can say "geçti" only on level 1
or 2 data, otherwise the result is a preliminary finding (`research_verdict`)."""

from __future__ import annotations

import contextvars
import functools
import json
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from core.config.paths import LOG_DIR

LEVEL_NAMES = {
    1: "resmî ya da lisanslı",
    2: "ikinci kaynakla doğrulanmış",
    3: "doğrulanmamış",
}
NOTE = "Veri: doğrulanmamış kaynak"
PASSED, PRELIMINARY, FAILED = "geçti", "ön bulgu", "geçmedi"

# the user's file check (core.market.second_source) writes this; the "Veri doğruluğu" SLO reads the same file
SECOND_SOURCE_FILE = LOG_DIR / "price_second_source.json"
CHECK_MAX_AGE = timedelta(days=8)  # as the SLO (slo.ACCURACY_MAX_AGE)
MAX_DIFFERING = 0.01  # as the SLO: at most 1 % of the stocks differ
CACHE_SECONDS = 60

# commands whose answer is built on price data (the note goes under their title on level 3)
DATA_COMMANDS = frozenset({
    "summary", "top", "analyze", "seviye", "karne", "tablo", "uzun", "uzun_liste", "piyasa", "senaryo", "risk",
    "watchscan", "portfolio", "denge", "performans", "yil", "stres", "tara", "tara_devam", "tara_aciklama",
    "tara_sanal",
})


@dataclass(frozen=True)
class Trust:
    level: int
    source: str

    def label(self) -> str:
        return f"{self.source} · Seviye {self.level} ({LEVEL_NAMES[self.level]})"


def weakest(*items: Trust) -> Trust:
    if not items:
        raise ValueError("en az bir veri kaynağı gerekir")
    return max(items, key=lambda t: t.level)


_cache: dict[str, tuple[float, Trust]] = {}


def clear_cache() -> None:
    _cache.clear()


def price_trust(now: datetime) -> Trust:
    """Yahoo prices: level 2 while a recent second-source check passed, else level 3. Never raises."""

    hit = _cache.get("price")
    if hit and time.monotonic() - hit[0] < CACHE_SECONDS:
        return hit[1]
    result = Trust(3, "Yahoo")
    try:
        data = json.loads(SECOND_SOURCE_FILE.read_text(encoding="utf-8"))
        day = date.fromisoformat(data["date"])
        checked = int(data["checked"])
        share = len(data.get("differing") or []) / checked
        if checked > 0 and now.date() - day <= CHECK_MAX_AGE and share <= MAX_DIFFERING:
            result = Trust(2, f"Yahoo, {data.get('source') or 'ikinci kaynak'} ile doğrulandı ({day:%d.%m})")
    except (OSError, ValueError, KeyError, TypeError, ZeroDivisionError):
        pass
    _cache["price"] = (time.monotonic(), result)
    return result


def with_note(text: str, t: Trust) -> str:
    """The note on its own line right under the title (the first line outside a <pre> block); level 1 and 2 add
    nothing; a text that already has it is returned as it is."""

    if t.level < 3 or NOTE in text:
        return text
    lines = text.split("\n")
    depth = 0
    for i, line in enumerate(lines):
        depth += line.count("<pre>") - line.count("</pre>")
        if depth <= 0:
            return "\n".join([*lines[: i + 1], NOTE, *lines[i + 1:]])
    return text + "\n" + NOTE


def research_verdict(significant: bool, t: Trust) -> str:
    if not significant:
        return FAILED
    return PASSED if t.level <= 2 else PRELIMINARY


def research_line(t: Trust) -> str:
    if t.level <= 2:
        return f"Veri güveni: {t.label()}; geçti kararı verilebilir."
    return (f"Veri güveni: {t.label()}. XU100'den anlamlı yüksek çıkan sonuçlar {PRELIMINARY} sayılır; "
            "geçti kararı yalnız Seviye 1 ya da 2 veriyle verilir.")


# --- Telegram: the note on messages built on data -------------------------------------------------------------

_data: contextvars.ContextVar[dict | None] = contextvars.ContextVar("trust_data", default=None)


@contextmanager
def data_message():
    """Messages sent inside this block are built on price data: the first one gets the note on level 3."""

    token = _data.set({"noted": False})
    try:
        yield
    finally:
        _data.reset(token)


def note_outgoing(text: str, now: datetime | None = None) -> str:
    """Called by the bot for every message: inside data_message(), the first message gets the note."""

    state = _data.get()
    if state is None or state["noted"] or not isinstance(text, str):
        return text
    state["noted"] = True
    from core.market.calendar import now_istanbul

    return with_note(text, price_trust(now or now_istanbul()))


def tagged(handler):
    """A command handler whose answer is built on price data."""

    @functools.wraps(handler)
    async def wrapper(update, context):
        with data_message():
            return await handler(update, context)

    wrapper.trust_data = True
    return wrapper


__all__ = ["DATA_COMMANDS", "FAILED", "LEVEL_NAMES", "NOTE", "PASSED", "PRELIMINARY", "Trust", "clear_cache",
           "data_message", "note_outgoing", "price_trust", "research_line", "research_verdict", "tagged", "weakest",
           "with_note"]
