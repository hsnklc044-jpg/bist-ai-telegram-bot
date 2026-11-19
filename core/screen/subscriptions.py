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

import pandas as pd

from core.config.paths import LOG_DIR, SCREEN_SUBSCRIPTIONS_FILE
from core.infrastructure.csvfiles import open_append, read_rows
from core.infrastructure.logger import get_logger
from core.screen.language import normalize, parse
from core.screen.templates import TEMPLATES

logger = get_logger(__name__)

SUBSCRIPTIONS_FILE = SCREEN_SUBSCRIPTIONS_FILE
STATE_FILE = LOG_DIR / "screen_subscriptions_state.json"
# K-114 (owner, 19.11.2026): the morning table keeps A100, GC and KRL. These two are left out of the morning
# table only; their definitions and subscriptions are kept (personal records are not edited).
MORNING_EXCLUDED = frozenset({"bist30_aday", "bist100_trend"})
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


def _price(value: float) -> str:
    return f"{value:.2f}".replace(".", ",")


def _level_lines(symbols, frames) -> list[str]:
    """The nearest cluster support and resistance of each listed stock; a stock without one is left out."""

    from core.analytics.levels import levels, nearest

    rows = []
    for symbol in sorted(symbols)[:MAX_LEVEL_LINES]:
        df = (frames or {}).get(symbol)
        if df is None:
            continue
        try:
            near = nearest([lv for lv in levels(df) if lv.method == "küme"], 1)
        except Exception:  # noqa: BLE001 - a level line never stops the list
            logger.exception("Levels failed for %s", symbol)
            continue
        parts = [f"{kind} {_price(found[0].price)} ({found[0].dist_pct:+.1f}%)".replace(".", ",")
                 for kind, found in near.items() if found]
        if parts:
            rows.append(f"  {symbol.removesuffix('.IS')}: " + " · ".join(parts))
    if not rows:
        return []
    more = len(symbols) - MAX_LEVEL_LINES
    tail = [f"  ve {more} hisse daha: /seviye KOD"] if more > 0 else []
    return ["Yakın destek ve direnç (küme):", *rows, *tail]


def _message(name: str, criteria: str, day: date, now: list[str], before: list[str] | None,
             note: str = "", frames=None) -> str | None:
    from core.screen.command import DISCLAIMER

    head = f"🔔 Tarama aboneliği: {name} ({criteria}) · veri {day:%d.%m.%Y}"
    if before is None:
        body = [f"İlk liste: {len(now)} hisse" + (f": {_codes(now)}" if now else " (şu an koşulu sağlayan yok).")]
        body += _level_lines(now, frames)
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
        body += _level_lines(entered, frames)
    if note:
        body.append(note)
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
            result = engine.run(query, frames, bench, found)
            symbols = sorted(m.symbol for m in result.matches)
        except Exception as exc:  # noqa: BLE001 - one screen never stops the others or the report
            logger.exception("Subscription %s failed", name)
            out.messages.append(f"⚠️ Tarama aboneliği {name} bugün çalıştırılamadı: {exc}")
            continue
        before = previous.get("symbols") if previous and previous.get("criteria") == criteria else None
        note = (f"(bugünkü rejim {result.regime}; rejim={query.regime} filtresi bugün listeyi boş bırakır, /piyasa)"
                if result.regime_blocked else "")
        message = _message(name, criteria, day, symbols, before, note, frames)
        if message:
            out.messages.append(message)
        out.state[name] = {"day": day.isoformat(), "criteria": criteria, "symbols": symbols}
    return out


def morning(day: date, live=None, path: Path | None = None, saved_path: Path | None = None, suspects=None,
            universe_of=None, usd=None, record_path: Path | None = None) -> list[str]:
    """
    Owner's instruction #15: one message (more only when Telegram's 4096 characters require it: the table goes
    on in the next message, each one starting with the warning line; every line is cut to fit, see
    core.screen.morning_table.pack) with ONE table, one row per stock and the codes of
    every subscribed screen it passed (core.screen.morning_table), from the last closes. The first line is the
    untested-filter warning; the bot adds the data line under it (core.market.trust). The rows are appended to
    the filter record (core.screen.filtre_kayitlari; a record failure never stops the message). It reads and
    changes no evening state. Nothing on a holiday or while the breaker or panic lock is on. HTML text.
    """

    import html

    from core.market.calendar import is_session_day
    from core.screen import engine, filtre_kayitlari, universe
    from core.screen import morning_table as mt
    from core.screen.command import DISCLAIMER, _live
    from core.signals import store

    subscribed = sorted((n, c) for n, c in active(path).items() if n not in MORNING_EXCLUDED)
    if not subscribed or not is_session_day(day) or store.locked(day):
        return []
    results: dict[str, list[str]] = {}
    frames_all: dict = {}
    gg: dict[str, float] = {}
    problems, empty, criteria_of_name = [], [], {}
    for name, chat in subscribed:
        criteria = criteria_of(name, saved_path)
        if criteria is None:
            continue
        try:
            query = parse(criteria)
            chat_id = int(chat) if str(chat).lstrip("-").isdigit() else None
            frames, bench = (live or _live)((universe_of or universe.symbols)(query.universe, chat_id))
            found = universe.suspects() if suspects is None else suspects
            matches = engine.run(query, frames, bench, found).matches
        except Exception as exc:  # noqa: BLE001 - one screen never stops the others
            logger.exception("Morning list %s failed", name)
            problems.append(f"⚠️ Sabah listesi {name} hazırlanamadı: {type(exc).__name__}: {exc}")
            continue
        criteria_of_name[name] = criteria
        results[name] = [m.symbol for m in matches]
        for m in matches:
            gg.setdefault(m.symbol, m.values.get("gg_20", float("nan")))
            frames_all.setdefault(m.symbol, frames.get(m.symbol))
        if not matches:
            empty.append(name)
    for screen, other, kind in mt.overlaps({n: set(s) for n, s in results.items()}):
        logger.info("Morning screens: %s is %s of %s today", screen, kind, other)

    by_symbol: dict[str, list[str]] = {}
    for name, symbols in results.items():
        for symbol in symbols:
            by_symbol.setdefault(symbol, []).append(name)
    if usd is None:
        try:
            from core.market import macro

            usd = macro.load_usdtry()
        except Exception:  # noqa: BLE001 - no rates: the USD column says "—"
            logger.exception("USD/TRY not read for the morning table")
            usd = pd.Series(dtype=float)
    rows = []
    for symbol, names in by_symbol.items():
        row = mt.Row(symbol, names, gg.get(symbol), event=mt.event_flag(symbol, day))
        df = frames_all.get(symbol)
        if df is not None and len(df):
            try:
                row.support_pct, row.resistance_pct, row.distance_atr = mt.nearest_levels(df)
            except Exception:  # noqa: BLE001 - a level never stops the table
                logger.exception("Levels failed for %s", symbol)
            row.usd = mt.usd_trend(df["close"], usd)
        rows.append(row)
    rows = mt.rank(rows)

    records = []
    for row in rows:
        df = frames_all.get(row.symbol)
        if df is not None and len(df):
            records.append(filtre_kayitlari.Record(row.symbol.removesuffix(".IS"), row.screens,
                                                   df.index[-1].date(), float(df["close"].iloc[-1])))
    try:
        filtre_kayitlari.append_records(records, day, record_path)
    except Exception:  # noqa: BLE001 - the record never stops the message
        logger.exception("Filter record not written")

    code_of = mt.codes(criteria_of_name)
    last = max((df.index.max() for df in frames_all.values() if df is not None and len(df)), default=None)
    head = "🌅 Sabah filtre tablosu" + (f" · son kapanış {last:%d.%m.%Y}" if last is not None else "")
    blocks = []
    if rows:
        try:
            blocks += mt.table_parts(rows, code_of)
        except Exception as exc:  # noqa: BLE001 - the rest of the message still goes out
            logger.exception("Morning table failed")
            problems.append(f"⚠️ Sabah tablosu hazırlanamadı: {type(exc).__name__}: {exc}")
        legend = "Kodlar: " + ", ".join(f"{code_of[n]}={n}" for n in sorted(criteria_of_name))
        blocks.append(html.escape(mt.short(legend, mt.BUDGET // 8)))
        blocks.append("GG: 20 seans göreli güç sırası (1 en yüksek) · D%/R%: en yakın küme destek/direnç uzaklığı · "
                      f"ATR: yakın seviyenin ATR cinsinden uzaklığı (&lt;1: {mt.NOISE}) · USD: dolar fiyatı 200 "
                      "günlük ortalamasının üstünde ↑, altında ↓ (gösterim alanı)")
    if empty:
        blocks.append(html.escape(mt.short(f"Hisse çıkmayan taramalar: {', '.join(empty)}.", mt.BUDGET // 8)))
    blocks += [html.escape(mt.short(p)) for p in problems]
    if rows:
        blocks.append("Koşul değerleri: /tara_aciklama KOD AD")
    blocks.append(DISCLAIMER)
    return mt.pack([mt.WARNING, html.escape(f"{head} · {len(rows)} hisse")], blocks,
                   html.escape(f"{head} (devam)"))


def save_state(outcome: Outcome, path: Path | None = None) -> None:
    path = Path(path or STATE_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.stem}.{os.getpid()}.tmp")  # one temp file per process (bot + report)
    tmp.write_text(json.dumps(outcome.state, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)


__all__ = ["MAX_SUBSCRIPTIONS", "Outcome", "active", "cancel_text", "list_text", "morning", "run", "save_state",
           "subscribe_text"]
