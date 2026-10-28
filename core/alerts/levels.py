"""
QuantBIST
Closing price alarms: "tell me when THYAO closes below 240". Checked once a day in the evening
report against the as-traded close of that session (no intraday prices, no live feed).

data/price_alarms.csv is append-only, like the ledger: setting, removing and triggering an alarm
each add a row, nothing is rewritten. The last row of an id decides its state.

    /alarm THYAO altında 240      /alarm EREGL üstünde 50,5
    /alarm                         (list)          /alarm sil 3

Information only: an alarm is a note the user set, not a buy or sell signal.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from core.config.paths import PRICE_ALARMS_FILE
from core.infrastructure.csvfiles import open_append, read_rows
from core.market.symbols import normalize_symbol

COLUMNS = ("id", "at", "symbol", "direction", "level", "event", "close")
DIRECTIONS = ("below", "above")
DIRECTION_WORDS = {
    "altında": "below", "altinda": "below", "altı": "below", "alti": "below", "<": "below",
    "üstünde": "above", "ustunde": "above", "üstü": "above", "ustu": "above", ">": "above",
}
USAGE = ("Kullanım: /alarm THYAO altında 240 · /alarm THYAO üstünde 300 · /alarm (liste) · /alarm sil 3\n"
         "Alarm yalnız akşam kapanışında kontrol edilir; gün içi fiyat izlenmez.")


@dataclass(frozen=True)
class Alarm:
    id: int
    symbol: str
    direction: str
    level: float


@dataclass(frozen=True)
class Hit:
    alarm: Alarm
    close: float


def _now() -> datetime:
    from core.market.calendar import now_istanbul

    return now_istanbul()


def _states(path: Path) -> dict[int, tuple[Alarm, str]]:
    states: dict[int, tuple[Alarm, str]] = {}
    for _, row in read_rows(path, COLUMNS):
        alarm_id = int(row["id"])
        if row["event"] == "kuruldu":
            alarm = Alarm(alarm_id, row["symbol"], row["direction"], float(row["level"]))
        elif alarm_id in states:
            alarm = states[alarm_id][0]
        else:
            continue
        states[alarm_id] = (alarm, row["event"])
    return states


def active(path: Path | None = None) -> list[Alarm]:
    return [a for a, event in _states(Path(path or PRICE_ALARMS_FILE)).values() if event == "kuruldu"]


def _append(path: Path, alarm: Alarm, event: str, at: datetime, close: float | None = None) -> None:
    fh, new_file = open_append(path)
    with fh:
        writer = csv.writer(fh)
        if new_file:
            writer.writerow(COLUMNS)
        writer.writerow([alarm.id, at.isoformat(timespec="seconds"), alarm.symbol, alarm.direction,
                         f"{alarm.level:g}", event, "" if close is None else f"{close:g}"])


def add(symbol: str, direction: str, level: float, path: Path | None = None, now: datetime | None = None) -> Alarm:
    path = Path(path or PRICE_ALARMS_FILE)
    if direction not in DIRECTIONS:
        raise ValueError(f"yön 'altında' ya da 'üstünde' olmalı: {direction!r}")
    if not level > 0:
        raise ValueError("seviye sıfırdan büyük olmalı")
    alarm = Alarm(max(_states(path), default=0) + 1, normalize_symbol(symbol), direction, float(level))
    _append(path, alarm, "kuruldu", now or _now())
    return alarm


def remove(alarm_id: int, path: Path | None = None, now: datetime | None = None) -> bool:
    path = Path(path or PRICE_ALARMS_FILE)
    state = _states(path).get(alarm_id)
    if not state or state[1] != "kuruldu":
        return False
    _append(path, state[0], "silindi", now or _now())
    return True


def check(day: date, closes: dict[str, float], path: Path | None = None, now: datetime | None = None,
          write: bool = True) -> list[Hit]:
    """Alarms whose stock closed beyond the level on `day`; each fires once (written as triggered)."""

    path = Path(path or PRICE_ALARMS_FILE)
    hits = []
    for alarm in active(path):
        close = closes.get(alarm.symbol)
        if close is None:
            continue
        if (alarm.direction == "below" and close < alarm.level) or (alarm.direction == "above" and close > alarm.level):
            hits.append(Hit(alarm, close))
    if write:
        mark(hits, path, now)
    return hits


def mark(hits: list[Hit], path: Path | None = None, now: datetime | None = None) -> None:
    """Write the hits as triggered (after the report carrying them was sent)."""

    path = Path(path or PRICE_ALARMS_FILE)
    for h in hits:
        _append(path, h.alarm, "tetiklendi", now or _now(), h.close)


def _describe(alarm: Alarm) -> str:
    from core.reports.daily import tr

    where = "altına inerse" if alarm.direction == "below" else "üstüne çıkarsa"
    return f"#{alarm.id} {alarm.symbol.removesuffix('.IS')} kapanış {tr(alarm.level, 2)}'ın {where}"


def format_hits(hits: list[Hit]) -> str:
    from core.reports.daily import tr

    lines = []
    for h in hits:
        where = "altında" if h.alarm.direction == "below" else "üstünde"
        lines.append(f"🔔 {h.alarm.symbol.removesuffix('.IS')} {tr(h.close, 2)} ile {tr(h.alarm.level, 2)}'ın "
                     f"{where} kapandı (alarm #{h.alarm.id}, bir kez bildirilir; al/sat önerisi değildir)")
    return "\n".join(lines)


def _number(text: str) -> float:
    return float(text.strip().replace(".", "").replace(",", ".") if "," in text else text.strip())


def command(words: list[str], path: Path | None = None, now: datetime | None = None) -> str:
    """The /alarm command's answer (and the file change it asks for)."""

    words = [w.strip() for w in words if w.strip()]
    if not words:
        alarms = active(path)
        if not alarms:
            return "🔔 Kurulu alarm yok.\n" + USAGE
        return "\n".join(["🔔 Kurulu alarmlar:"] + [f"  {_describe(a)}" for a in alarms]
                         + ["Alarm yalnız akşam kapanışında kontrol edilir; gün içi fiyat izlenmez."])
    if words[0].lower() == "sil":
        if len(words) != 2 or not words[1].lstrip("#").isdigit():
            return USAGE
        alarm_id = int(words[1].lstrip("#"))
        return f"🔔 Alarm #{alarm_id} silindi." if remove(alarm_id, path, now) else f"Alarm #{alarm_id} bulunamadı."
    if len(words) != 3 or words[1].lower() not in DIRECTION_WORDS:
        return USAGE
    try:
        alarm = add(words[0], DIRECTION_WORDS[words[1].lower()], _number(words[2]), path, now)
    except ValueError as exc:
        return f"{exc}\n{USAGE}" if "Geçersiz" in str(exc) or "seviye" in str(exc) else USAGE
    return f"🔔 Alarm kuruldu: {_describe(alarm)}. Akşam raporunda bir kez bildirilir."


__all__ = ["Alarm", "Hit", "active", "add", "check", "command", "format_hits", "mark", "remove"]
