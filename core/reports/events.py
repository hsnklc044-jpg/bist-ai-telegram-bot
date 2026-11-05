"""
QuantBIST
Dividend and corporate event calendar (road plan part 2; 05.11.2026). There is no automated
access to KAP (K-48: its terms for automated fetching are not confirmed), so the calendar holds
what the user writes, from KAP or the company, by hand:

    /takvim                                   the next WINDOW days, stocks held or watched
    /takvim hepsi                             every future entry
    /takvim ekle THYAO 05.12.2026 temettü 3,25 TL brüt
    /takvim sil 3

data/events.csv is a personal file, append-only: a deletion is a new row, nothing is overwritten.
The weekly health report lists the coming entries of the stocks held.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from core.config.paths import EVENTS_FILE

WINDOW = 30
COLUMNS = ("at", "action", "id", "symbol", "date", "text")
USAGE = ("Kullanım: /takvim · /takvim hepsi · /takvim ekle KOD GG.AA.YYYY açıklama (ör. /takvim ekle THYAO "
         "05.12.2026 temettü 3,25 TL brüt) · /takvim sil NO. Kayıtlar elle girilir (KAP'a otomatik erişim yok).")


class EventError(ValueError):
    pass


@dataclass(frozen=True)
class Event:
    id: int
    symbol: str
    day: date
    text: str


def _path(path) -> Path:
    return Path(path or EVENTS_FILE)


def load(path=None) -> list[Event]:
    from core.infrastructure.csvfiles import read_rows

    path = _path(path)
    if not path.exists():
        return []
    events: dict[int, Event] = {}
    for _, row in read_rows(path, COLUMNS):
        try:
            number = int(row["id"])
        except ValueError:
            continue
        if row["action"] == "sil":
            events.pop(number, None)
        elif row["action"] == "ekle":
            try:
                events[number] = Event(number, row["symbol"], date.fromisoformat(row["date"]), row["text"])
            except ValueError:
                continue
    return sorted(events.values(), key=lambda e: (e.day, e.symbol, e.id))


def _append(path: Path, row: dict) -> None:
    from core.infrastructure.csvfiles import open_append

    fh, new_file = open_append(path)
    with fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        if new_file:
            writer.writeheader()
        writer.writerow(row)


def _next_id(path: Path) -> int:
    from core.infrastructure.csvfiles import read_rows

    if not path.exists():
        return 1
    ids = [int(r["id"]) for _, r in read_rows(path, COLUMNS) if r["id"].isdigit()]
    return max(ids, default=0) + 1


def _day(text: str) -> date:
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    raise EventError(f"tarih okunamadı: {text!r} (GG.AA.YYYY)")


def add(words: list[str], path=None, now: datetime | None = None) -> Event:
    from core.ledger.book import normalize_symbol

    if len(words) < 3:
        raise EventError("kod, tarih ve açıklama gerekli")
    try:
        symbol = normalize_symbol(words[0])
    except ValueError as exc:
        raise EventError(str(exc)) from exc
    day = _day(words[1])
    text = " ".join(words[2:]).strip()
    path = _path(path)
    event = Event(_next_id(path), symbol, day, text)
    _append(path, {"at": (now or datetime.now()).isoformat(timespec="seconds"), "action": "ekle", "id": event.id,
                   "symbol": symbol, "date": day.isoformat(), "text": text})
    return event


def delete(number: int, path=None, now: datetime | None = None) -> Event:
    path = _path(path)
    found = next((e for e in load(path) if e.id == number), None)
    if found is None:
        raise EventError(f"#{number} numaralı kayıt yok")
    _append(path, {"at": (now or datetime.now()).isoformat(timespec="seconds"), "action": "sil", "id": number,
                   "symbol": found.symbol, "date": found.day.isoformat(), "text": ""})
    return found


def _line(e: Event, today: date, held: set[str], watched: set[str]) -> str:
    days = (e.day - today).days
    when = "bugün" if days == 0 else f"{days} gün sonra"
    tag = " [portföyde]" if e.symbol in held else (" [izlemede]" if e.symbol in watched else "")
    return f"  #{e.id} {e.symbol.removesuffix('.IS')} {e.day:%d.%m.%Y} ({when}): {e.text}{tag}"


def upcoming(path=None, today: date | None = None, symbols: set[str] | None = None, window: int | None = WINDOW
             ) -> list[Event]:
    today = today or date.today()
    return [e for e in load(path) if e.day >= today and (window is None or (e.day - today).days <= window)
            and (symbols is None or e.symbol in symbols)]


def upcoming_lines(path=None, today: date | None = None, held: set[str] | None = None) -> list[str]:
    """For the weekly health report: the coming entries of the stocks held."""

    today = today or date.today()
    return [_line(e, today, held or set(), set()) for e in upcoming(path, today, held or set())]


def _held_and_watched() -> tuple[set[str], set[str]]:
    held: set[str] = set()
    try:
        from core.ledger.book import load_ledger, open_positions

        entries = load_ledger()
        held = {p.symbol for account in ("real", "paper") for p in open_positions(entries, account)}
    except Exception:  # noqa: BLE001 - an unreadable ledger leaves the calendar usable
        pass
    watched: set[str] = set()
    try:
        from core.watchlist.repository import load_watchlist

        for symbols in load_watchlist().values():
            watched |= set(symbols)
    except Exception:  # noqa: BLE001
        pass
    return held, watched


def command_text(words: list[str], path=None, today: date | None = None, held: set[str] | None = None,
                 watched: set[str] | None = None) -> str:
    today = today or date.today()
    words = [w for w in words if w.strip()]
    try:
        if words and words[0].lower() == "ekle":
            e = add(words[1:], path)
            return f"🗓 Eklendi #{e.id}: {e.symbol.removesuffix('.IS')} {e.day:%d.%m.%Y} – {e.text}"
        if words and words[0].lower() == "sil":
            if len(words) != 2 or not words[1].lstrip("#").isdigit():
                raise EventError("silmek için kayıt numarası gerekli (ör. /takvim sil 3)")
            e = delete(int(words[1].lstrip("#")), path)
            return f"🗑 Silindi #{e.id}: {e.symbol.removesuffix('.IS')} {e.day:%d.%m.%Y} – {e.text}"
        if words and words[0].lower() not in ("hepsi", "tum", "tümü"):
            raise EventError(f"anlaşılmadı: {words[0]!r}")
    except EventError as exc:
        return f"⚠️ {exc}\n{USAGE}"
    if held is None or watched is None:
        found_held, found_watched = _held_and_watched()
        held = found_held if held is None else held
        watched = found_watched if watched is None else watched
    every = bool(words)
    events = upcoming(path, today, None if every else held | watched, None if every else WINDOW)
    title = ("🗓 Takvim: bütün gelecek kayıtlar" if every else
             f"🗓 Takvim: portföydeki ve izlemedeki hisseler, önümüzdeki {WINDOW} gün")
    lines = [title] + ([_line(e, today, held, watched) for e in events] or ["  Kayıt yok."])
    lines.append("Kayıtlar elle girilir; tarih ve tutarı KAP'tan doğrulayın. Bilgi amaçlıdır, öneri değildir.")
    return "\n".join(lines)


__all__ = ["Event", "EventError", "USAGE", "add", "command_text", "delete", "load", "upcoming", "upcoming_lines"]
