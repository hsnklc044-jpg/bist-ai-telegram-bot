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
USAGE = "Kullanım: /tara_abone AD (kayıtlı tarama ya da şablon; /tara_liste, /tara_sablonlar)"
CANCEL_USAGE = "Kullanım: /tara_abone_iptal AD (abonelikler: /tara_abonelikler)"


@dataclass
class Outcome:
    messages: list[str] = field(default_factory=list)
    state: dict = field(default_factory=dict)  # written by save_state once the messages went out


def active(path: Path | None = None) -> dict[str, str]:
    """name -> chat of the subscriptions in force (the last row for a name decides)."""

    path = Path(path or SUBSCRIPTIONS_FILE)
    found: dict[str, str] = {}
    for _, row in read_rows(path, COLUMNS):
        if row["action"] == SUBSCRIBE:
            found[row["name"]] = row["chat"]
        else:
            found.pop(row["name"], None)
    return found


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
    if not current:
        return "Abonelik yok. Başlatmak için: /tara_abone AD\nFiltre sonucudur, yatırım önerisi değildir."
    lines = [f"🔔 Abonelikler ({len(current)}/{MAX_SUBSCRIPTIONS}), her işlem günü 18:30 raporundan sonra:"]
    lines += [f"  {name}: {criteria_of(name, saved_path) or '(tarama bulunamadı)'}" for name in sorted(current)]
    lines += ["İptal: /tara_abone_iptal AD", "Filtre sonucudur, yatırım önerisi değildir."]
    return "\n".join(lines)


# --- the evening run ------------------------------------------------------------------------------


def _load_state(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (OSError, ValueError):
        return {}


def _codes(symbols) -> str:
    return ", ".join(s.removesuffix(".IS") for s in sorted(symbols))


def _message(name: str, criteria: str, day: date, now: list[str], before: list[str] | None) -> str | None:
    from core.screen.command import DISCLAIMER

    head = f"🔔 Tarama aboneliği: {name} ({criteria}) · veri {day:%d.%m.%Y}"
    if before is None:
        body = [f"İlk liste: {len(now)} hisse" + (f": {_codes(now)}" if now else " (şu an koşulu sağlayan yok).")]
    else:
        entered, left = set(now) - set(before), set(before) - set(now)
        if not entered and not left:
            return None
        body = []
        if entered:
            body.append(f"➕ Girenler: {_codes(entered)}")
        if left:
            body.append(f"➖ Çıkanlar: {_codes(left)}")
        body.append(f"Şimdi {len(now)} hisse.")
    return "\n".join([head, *body, f"Ayrıntı ve karne: /tara {name}", DISCLAIMER])


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
            symbols = sorted(m.symbol for m in engine.run(query, frames, bench, found).matches)
        except Exception as exc:  # noqa: BLE001 - one screen never stops the others or the report
            logger.exception("Subscription %s failed", name)
            out.messages.append(f"⚠️ Tarama aboneliği {name} bugün çalıştırılamadı: {exc}")
            continue
        before = previous.get("symbols") if previous and previous.get("criteria") == criteria else None
        message = _message(name, criteria, day, symbols, before)
        if message:
            out.messages.append(message)
        out.state[name] = {"day": day.isoformat(), "criteria": criteria, "symbols": symbols}
    return out


def save_state(outcome: Outcome, path: Path | None = None) -> None:
    path = Path(path or STATE_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(outcome.state, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)


__all__ = ["MAX_SUBSCRIPTIONS", "Outcome", "active", "cancel_text", "list_text", "run", "save_state",
           "subscribe_text"]
