"""
QuantBIST
/tara subscriptions (DECISIONS K-42): /tara_abone AD runs a saved screen or a ready-made template
after the 18:30 report and sends only the stocks that entered or left the list; no change, no
message. The report decides the day: no report (holiday, no new candle, already sent) means no
run. data/screen_subscriptions.csv is personal and append-only (a row per subscribe or cancel);
the last lists are a derived state in logs/.
"""

from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from core.config.paths import LOG_DIR, SCREEN_SUBSCRIPTIONS_FILE
from core.infrastructure.csvfiles import open_append, read_rows
from core.infrastructure.logger import get_logger
from core.screen.language import normalize, parse
from core.screen.templates import TEMPLATES

logger = get_logger(__name__)

SUBSCRIPTIONS_FILE = SCREEN_SUBSCRIPTIONS_FILE
STATE_FILE = LOG_DIR / "screen_subscriptions_state.json"
COLUMNS = ("at", "chat", "name", "action")
SUBSCRIBE, CANCEL = "abone", "iptal"
MAX_SUBSCRIPTIONS = 5
MAX_LEVEL_LINES = 40  # keeps the message inside Telegram's limit
USAGE = "Kullanım: /tara_abone AD (kayıtlı tarama ya da şablon; /tara_liste, /tara_sablonlar)"
CANCEL_USAGE = "Kullanım: /tara_abone_iptal AD (abonelikler: /tara_abonelikler)"


@dataclass
class Outcome:
    messages: list[str] = field(default_factory=list)
    state: dict = field(default_factory=dict)  # written by save_state once the messages went out


# E madde 4 (the user's 11.11.2026 decision): closed, not deleted. The subscription file is a personal record and
# stays as it is; a subscription to one of these made before CLOSED_AT is simply not in force. Subscribing again
# later works as usual.
CLOSED = ("bist100_aday", "bist30_aday", "bist100_trend")
CLOSED_AT = "2026-11-12"


def _closed(name: str, at: str) -> bool:
    return name in CLOSED and at[:10] < CLOSED_AT


def active(path: Path | None = None) -> dict[str, str]:
    """name -> chat of the subscriptions in force (the last row for a name decides)."""

    path = Path(path or SUBSCRIPTIONS_FILE)
    found: dict[str, str] = {}
    for _, row in read_rows(path, COLUMNS):
        if row["action"] == SUBSCRIBE and not _closed(row["name"], row["at"]):
            found[row["name"]] = row["chat"]
        else:
            found.pop(row["name"], None)
    return found


def closed(path: Path | None = None) -> list[str]:
    """The subscriptions closed by the 11.11.2026 decision that were in force before it."""

    path = Path(path or SUBSCRIPTIONS_FILE)
    last: dict[str, dict] = {}
    for _, row in read_rows(path, COLUMNS):
        last[row["name"]] = row
    return sorted(n for n, r in last.items() if r["action"] == SUBSCRIBE and _closed(n, r["at"]))


def _append(path: Path, chat_id, name: str, action: str, now: datetime | None) -> None:
    from core.market.calendar import now_istanbul

    fh, new_file = open_append(path)
    with fh:
        writer = csv.writer(fh, lineterminator="\n")
        if new_file:
            writer.writerow(COLUMNS)
        writer.writerow([(now or now_istanbul()).isoformat(timespec="seconds"), chat_id, name, action])


def criteria_of(name: str, saved_path: Path | None = None) -> str | None:
    from core.screen.command import load_saved

    if name in TEMPLATES:
        return TEMPLATES[name].criteria
    return load_saved(saved_path).get(name)


def subscribe_text(words: list[str], chat_id, path: Path | None = None, saved_path: Path | None = None,
                   now: datetime | None = None) -> str:
    path = Path(path or SUBSCRIPTIONS_FILE)
    if len(words) != 1:
        return USAGE
    name = normalize(words[0])
    criteria = criteria_of(name, saved_path)
    if criteria is None:
        return f"⚠️ '{name}' adında kayıtlı tarama ya da şablon yok. " + USAGE
    current = active(path)
    if name in current:
        return f"'{name}' aboneliği zaten var. Abonelikler: /tara_abonelikler"
    if len(current) >= MAX_SUBSCRIPTIONS:
        return f"⚠️ En fazla {MAX_SUBSCRIPTIONS} abonelik olabilir. İptal: /tara_abone_iptal AD"
    _append(path, chat_id, name, SUBSCRIBE, now)
    return (f"🔔 Abone olundu: {name} ({criteria}). Her işlem günü 18:30 raporundan sonra çalışır; yalnız listeye "
            "giren ve çıkan hisseler gelir, değişiklik yoksa mesaj gelmez. Tatilde çalışmaz.\n"
            "Filtre sonucudur, yatırım önerisi değildir.")


def cancel_text(words: list[str], chat_id, path: Path | None = None, now: datetime | None = None) -> str:
    path = Path(path or SUBSCRIPTIONS_FILE)
    if len(words) != 1:
        return CANCEL_USAGE
    name = normalize(words[0])
    if name not in active(path):
        return f"'{name}' taramasına abone değilsin. " + CANCEL_USAGE
    _append(path, chat_id, name, CANCEL, now)
    return f"🔕 İptal edildi: {name}."


def end_for_deleted(name: str, path: Path | None = None, now: datetime | None = None) -> None:
    """A deleted saved screen takes its subscription with it (a template of that name stays)."""

    path = Path(path or SUBSCRIPTIONS_FILE)
    current = active(path)
    if name in current and name not in TEMPLATES:
        _append(path, current[name], name, CANCEL, now)


def list_text(path: Path | None = None, saved_path: Path | None = None) -> str:
    current = active(path)
    gone = closed(path)
    tail = [f"Kapatılan (kullanıcı kararı 11.11.2026; kayıt duruyor, yeniden açmak: /tara_abone AD): {', '.join(gone)}"
            ] if gone else []
    if not current:
        return "\n".join(["Abonelik yok. Başlatmak için: /tara_abone AD", *tail,
                          "Filtre sonucudur, yatırım önerisi değildir."])
    lines = [f"🔔 Abonelikler ({len(current)}/{MAX_SUBSCRIPTIONS}), her işlem günü 18:30 raporundan sonra:"]
    lines += [f"  {name}: {criteria_of(name, saved_path) or '(tarama bulunamadı)'}" for name in sorted(current)]
    lines += [*tail, "İptal: /tara_abone_iptal AD", "Filtre sonucudur, yatırım önerisi değildir."]
    return "\n".join(lines)


# --- the evening run ------------------------------------------------------------------------------


def _load_state(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (OSError, ValueError):
        return {}


def _codes(symbols) -> str:
    return ", ".join(s.removesuffix(".IS") for s in sorted(symbols))


def _price(value: float) -> str:
    return f"{value:.2f}".replace(".", ",")


TABLE_ROWS = 5  # the message style: at most five stocks in a subscription message (H)


def _num(value: float | None) -> str:
    from core.reports.style import number

    return "—" if value is None else number(value, 0 if value >= 1000 else 2)


def _table(symbols, frames, bench_close) -> list[str]:
    """The listed stocks, best professional score first (at most TABLE_ROWS): colour, code, score, close, the
    nearest support (/seviye's own levels). Relative strength is ranked in the scanned universe."""

    from core.analytics import pro_score
    from core.analytics.levels import levels, nearest

    present = {s: frames[s] for s in symbols if s in (frames or {}) and len(frames[s])}
    if not present:
        return []
    try:
        scores = pro_score.latest(present, bench_close, universe=frames) if bench_close is not None else {}
    except Exception:  # noqa: BLE001 - a missing score never stops the list
        logger.exception("Scores failed for the subscription table")
        scores = {}

    def rank(symbol):
        sc = scores.get(symbol)
        return (-(sc.total if sc is not None and not sc.missing else -1), symbol)

    rows = [f"{'':2}{'Hisse':<6}{'Puan':>4}{'Fiyat':>9}{'Destek':>9}"]
    for symbol in sorted(present, key=rank)[:TABLE_ROWS]:
        sc = scores.get(symbol)
        colour = sc.colour() if sc is not None else None
        points = str(sc.total) if sc is not None and not sc.missing else "—"
        try:
            found = nearest(levels(present[symbol]), 1)["destek"]
            support = found[0].price if found else None
        except Exception:  # noqa: BLE001 - a missing level never stops the list
            logger.exception("Levels failed for %s", symbol)
            support = None
        rows.append(f"{colour[0] if colour else '·'} {symbol.removesuffix('.IS'):<6}{points:>4}"
                    f"{_num(float(present[symbol]['close'].iloc[-1])):>9}{_num(support):>9}")
    out = ["<pre>" + "\n".join(rows) + "</pre>"]
    if len(present) > TABLE_ROWS:
        out.append(f"ve {len(present) - TABLE_ROWS} hisse daha")
    return out


def _message(name: str, criteria: str, day: date, now: list[str], before: list[str] | None,
             note: str = "", frames=None, bench_close=None) -> str | None:
    """The evening message in the message style (H): only when something changed (or the first list)."""

    from core.reports.style import header

    if before is None:
        second = f"İlk liste · {len(now)} hisse" if now else "İlk liste · şu an koşulu sağlayan hisse yok"
        shown, left = now, set()
    else:
        entered, left = set(now) - set(before), set(before) - set(now)
        if not entered and not left:
            return None
        second = " · ".join(x for x in (f"{len(entered)} yeni" if entered else "",
                                         f"{len(left)} çıkan" if left else "") if x)
        shown = sorted(entered)
    lines = [header(f"Tarama · {name.upper()}", day), second, *_table(shown, frames, bench_close)]
    if left:
        lines.append(f"Çıkan: {_codes(left)}")
    if note:
        lines.append(note)
    lines.append(f"/tara {name}")
    return "\n".join(lines)


def run(day: date, live=None, path: Path | None = None, saved_path: Path | None = None,
        state_path: Path | None = None, suspects=None, universe_of=None) -> Outcome:
    """The messages for `day` and the state to keep; nothing is written here."""

    from core.screen import engine, universe
    from core.screen.command import _live

    state = _load_state(Path(state_path or STATE_FILE))
    out = Outcome(state=dict(state))
    for name, chat in sorted(active(path).items()):
        criteria = criteria_of(name, saved_path)
        if criteria is None:
            continue  # the screen was removed by hand; the list says so
        previous = state.get(name)
        if previous and previous.get("day") == day.isoformat() and previous.get("criteria") == criteria:
            continue  # this data day ran already
        try:
            query = parse(criteria)
            chat_id = int(chat) if str(chat).lstrip("-").isdigit() else None
            frames, bench = (live or _live)((universe_of or universe.symbols)(query.universe, chat_id))
            found = universe.suspects() if suspects is None else suspects
            result = engine.run(query, frames, bench, found)
            symbols = sorted(m.symbol for m in result.matches)
        except Exception as exc:  # noqa: BLE001 - one screen never stops the others or the report
            logger.exception("Subscription %s failed", name)
            out.messages.append(f"⚠️ Tarama aboneliği {name} bugün çalıştırılamadı: {exc}")
            continue
        before = previous.get("symbols") if previous and previous.get("criteria") == criteria else None
        note = (f"(bugünkü rejim {result.regime}; rejim={query.regime} filtresi bugün listeyi boş bırakır, /piyasa)"
                if result.regime_blocked else "")
        message = _message(name, criteria, day, symbols, before, note, frames, bench["close"])
        if message:
            out.messages.append(message)
        out.state[name] = {"day": day.isoformat(), "criteria": criteria, "symbols": symbols}
    return out


def morning(day: date, live=None, path: Path | None = None, saved_path: Path | None = None, suspects=None,
            universe_of=None) -> list[str]:
    """
    The full candidate list of every subscription before the session, from the last closes. It reads and
    changes no evening state, so the 18:30 changes message stays as it was. Nothing on a holiday or while
    the breaker or panic lock is on.
    """

    from core.market.calendar import is_session_day
    from core.reports.style import header
    from core.screen import engine, universe
    from core.screen.command import _live
    from core.signals import store

    subscribed = sorted(active(path).items())
    if not subscribed or not is_session_day(day) or store.locked(day):
        return []
    messages, empty = [], []
    for name, chat in subscribed:
        criteria = criteria_of(name, saved_path)
        if criteria is None:
            continue
        try:
            query = parse(criteria)
            chat_id = int(chat) if str(chat).lstrip("-").isdigit() else None
            frames, bench = (live or _live)((universe_of or universe.symbols)(query.universe, chat_id))
            found = universe.suspects() if suspects is None else suspects
            symbols = [m.symbol for m in engine.run(query, frames, bench, found).matches]
        except Exception as exc:  # noqa: BLE001 - one screen never stops the others
            logger.exception("Morning list %s failed", name)
            messages.append(f"⚠️ Sabah listesi {name} hazırlanamadı: {exc}")
            continue
        if not symbols:
            empty.append(name)
            continue
        last = max(df.index.max() for df in frames.values() if len(df))
        messages.append("\n".join([header(f"Tarama · {name.upper()}", last.date()), f"Sabah listesi · {len(symbols)} hisse",
                                   *_table(symbols, frames, bench["close"]), f"/tara {name}"]))
    if empty:
        messages.append(f"{header('Sabah taramaları', day)}\nHisse çıkmayan: {', '.join(empty)}")
    return messages


def save_state(outcome: Outcome, path: Path | None = None) -> None:
    path = Path(path or STATE_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.stem}.{os.getpid()}.tmp")  # one temp file per process (bot + report)
    tmp.write_text(json.dumps(outcome.state, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)


__all__ = ["MAX_SUBSCRIPTIONS", "Outcome", "active", "cancel_text", "list_text", "morning", "run", "save_state",
           "subscribe_text"]
