"""
QuantBIST
Service level objectives (docs/CHARTER.md §2), measured over the last 7 days.

Each objective is computed from local records only; what cannot be measured here
is shown as unknown, never as healthy. Records kept for this (logs/, no personal data):

    heartbeats.csv      at,pid            one row per bot heartbeat (5 minutes)
    freshness.csv       date,checked_at,have,total,xu100   after each daily price update
    restore_tests.csv   at,ok,detail      after each weekly restore test

A gap between two heartbeats of the same process is the PC asleep (the process was
suspended); a new process id is a restart (PC switched on, task restarted the bot).
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path

from core.config.paths import LOG_DIR
from core.infrastructure.csvfiles import open_append
from core.market.calendar import ISTANBUL, is_session_day
from core.reports.health import OK, UNKNOWN, WARN

WINDOW = timedelta(days=7)
DEADLINE = time(19, 0)  # report and fresh prices by 19:00 on a session day
BEAT = timedelta(minutes=5)
MIN_HISTORY = timedelta(days=1)

HEARTBEATS_FILE = LOG_DIR / "heartbeats.csv"
FRESHNESS_FILE = LOG_DIR / "freshness.csv"
RESTORE_FILE = LOG_DIR / "restore_tests.csv"

TARGETS = {
    "Rapor teslimi": "≥ %99 seans 19:00'a kadar",
    "Bot ayakta kalma": "≥ %98",
    "Veri tazeliği": "≥ %98 hisse 19:00'da güncel",
    "Veri doğruluğu": "≤ %1 hisse ikinci kaynaktan farklı",
    "Yedek": "her gün + haftalık geri yükleme testi",
    "Kayıt bütünlüğü": "0 bozuk / tekrar / eksik",
    "Kalite (CI, kapsam)": "CI yeşil, kapsam ≥ %90",
}


@dataclass
class SloResult:
    name: str
    state: str
    value: float | None
    text: str

    def line(self) -> str:
        value = "—" if self.value is None else f"%{self.value * 100:.1f}"
        return f"{self.state} {self.name}: {value} (hedef {TARGETS[self.name]}) · {self.text}"


def _sessions(now: datetime) -> list[date]:
    """Session days in the window that should be complete by now (today only after 19:00)."""

    days = [now.date() - timedelta(days=i) for i in range(WINDOW.days)][::-1]
    if now.time() < DEADLINE:
        days = days[:-1]
    return [d for d in days if is_session_day(d)]


def _since(sessions: list[date], first: date | None) -> tuple[list[date], str]:
    """Sessions from the first record on: days before it were not measured, so they are no failures."""

    if first is None or not sessions or first <= sessions[0]:
        return sessions, ""
    return [d for d in sessions if d >= first], f"ölçüm {first:%d.%m}'de başladı"


def _deadline(day: date) -> datetime:
    return datetime.combine(day, DEADLINE, tzinfo=ISTANBUL)


def _rows(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as fh:
        return [r for r in csv.DictReader(fh) if None not in r and None not in r.values()]


def _when(text: str) -> datetime | None:
    try:
        moment = datetime.fromisoformat(text)
    except (TypeError, ValueError):
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=ISTANBUL)


def _days(days: list[date]) -> str:
    return ", ".join(f"{d:%d.%m}" for d in days)


# --- report delivery ----------------------------------------------------------------------------


def report_delivery(now: datetime, runs_path: Path) -> SloResult:
    from core.reports.runs import SENT

    name = "Rapor teslimi"
    if not Path(runs_path).exists():
        return SloResult(name, UNKNOWN, None, "runs.csv yok")
    rows = _rows(Path(runs_path))
    starts = [t.date() for r in rows if (t := _when(r["started_at"]))]
    sessions, started = _since(_sessions(now), min(starts) if starts else None)
    if not sessions:
        return SloResult(name, UNKNOWN, None, "pencerede ölçülmüş seans yok" + (f"; {started}" if started else ""))
    sent: dict[str, list[datetime]] = {}
    for r in rows:
        if r["status"] == SENT and (finished := _when(r["finished_at"])):
            sent.setdefault(r["data_day"], []).append(finished)
    on_time, late, missing = [], [], []
    for d in sessions:
        times = sent.get(d.isoformat(), [])
        (on_time if any(t <= _deadline(d) for t in times) else late if times else missing).append(d)
    start = now.date() - WINDOW + timedelta(days=1)
    twice = [date.fromisoformat(k) for k, v in sent.items() if len(v) > 1 and start <= date.fromisoformat(k)]
    closed = [date.fromisoformat(k) for k in sent if start <= date.fromisoformat(k) and not is_session_day(
        date.fromisoformat(k))]
    value = len(on_time) / len(sessions)
    notes = [f"{len(on_time)}/{len(sessions)} seans zamanında"]
    notes += [f"geç: {_days(late)}"] if late else []
    notes += [f"eksik: {_days(missing)}"] if missing else []
    notes += [f"iki kez: {_days(sorted(twice))}"] if twice else []
    notes += [f"tatilde gönderim: {_days(sorted(closed))}"] if closed else []
    notes += [started] if started else []
    ok = value >= 0.99 and not twice and not closed
    return SloResult(name, OK if ok else WARN, value, "; ".join(notes))


# --- bot uptime -----------------------------------------------------------------------------------


def record_heartbeat(path: Path | None = None, now: datetime | None = None, pid: int | None = None) -> None:
    from core.market.calendar import now_istanbul

    fh, new = open_append(Path(path or HEARTBEATS_FILE))
    with fh:
        if new:
            fh.write("at,pid\n")
        fh.write(f"{(now or now_istanbul()).isoformat(timespec='seconds')},{pid or os.getpid()}\n")


def bot_uptime(now: datetime, path: Path) -> SloResult:
    name = "Bot ayakta kalma"
    path = Path(path)
    beats = []
    if path.exists():
        for r in _rows(path):
            at = _when(r["at"])
            if at is not None and now - WINDOW <= at <= now:
                beats.append((at, r["pid"]))
    beats.sort()
    if not beats or now - beats[0][0] < MIN_HISTORY:
        first = f" (ilk kayıt {beats[0][0]:%d.%m %H:%M})" if beats else ""
        return SloResult(name, UNKNOWN, None, f"veri birikiyor{first}; en az 1 günlük yaşam sinyali gerekir")

    start = max(now - WINDOW, beats[0][0])
    total = now - start
    down, sleep, restarts = timedelta(), timedelta(), 0
    for (t1, p1), (t2, p2) in zip(beats, beats[1:], strict=False):
        if p1 != p2:
            restarts += 1
        gap = t2 - t1 - BEAT
        if gap > BEAT:
            down += gap
            if p1 == p2:
                sleep += gap
    tail = now - beats[-1][0] - BEAT
    if tail > BEAT:
        down += tail
    value = 1 - down / total
    hours = sleep.total_seconds() / 3600
    text = f"son sinyal {beats[-1][0]:%d.%m %H:%M}; bunun içinde uyku/askı {hours:.0f} saat; {restarts} yeniden başlama"
    return SloResult(name, OK if value >= 0.98 else WARN, value, text)


# --- data freshness -------------------------------------------------------------------------------


def record_freshness(day: date, have: int, total: int, xu100: bool, path: Path | None = None,
                     now: datetime | None = None) -> None:
    from core.market.calendar import now_istanbul

    fh, new = open_append(Path(path or FRESHNESS_FILE))
    with fh:
        if new:
            fh.write("date,checked_at,have,total,xu100\n")
        fh.write(f"{day.isoformat()},{(now or now_istanbul()).isoformat(timespec='seconds')},{have},{total},"
                 f"{int(bool(xu100))}\n")


def freshness(now: datetime, path: Path) -> SloResult:
    name = "Veri tazeliği"
    path = Path(path)
    if not path.exists():
        return SloResult(name, UNKNOWN, None, "freshness.csv yok (ilk raporla başlar)")
    rows = _rows(path)
    firsts = [date.fromisoformat(r["date"]) for r in rows]
    sessions, started = _since(_sessions(now), min(firsts) if firsts else None)
    if not sessions:
        return SloResult(name, UNKNOWN, None, "pencerede ölçülmüş seans yok" + (f"; {started}" if started else ""))
    by_day: dict[str, list[dict]] = {}
    for r in rows:
        by_day.setdefault(r["date"], []).append(r)
    good, notes = 0, []
    for d in sessions:
        rows = [r for r in by_day.get(d.isoformat(), []) if (t := _when(r["checked_at"])) and t <= _deadline(d)]
        if not rows:
            notes.append(f"{d:%d.%m} 19:00'a kadar ölçüm yok")
            continue
        r = rows[-1]
        share = int(r["have"]) / max(int(r["total"]), 1)
        if r["xu100"] != "1":
            notes.append(f"{d:%d.%m} XU100 yok")
        elif share < 0.98:
            notes.append(f"{d:%d.%m} %{share * 100:.0f}")
        else:
            good += 1
    value = good / len(sessions)
    text = f"{good}/{len(sessions)} seans" + (f"; {', '.join(notes)}" if notes else "") + (f"; {started}" if started else "")
    return SloResult(name, OK if value >= 0.99 else WARN, value, text)


# --- backups --------------------------------------------------------------------------------------


def record_restore_test(ok: bool, detail: str = "", path: Path | None = None, now: datetime | None = None) -> None:
    from core.market.calendar import now_istanbul

    fh, new = open_append(Path(path or RESTORE_FILE))
    with fh:
        writer = csv.writer(fh, lineterminator="\n")
        if new:
            writer.writerow(["at", "ok", "detail"])
        writer.writerow([(now or now_istanbul()).isoformat(timespec="seconds"), int(ok), detail[:200]])


def backup_slo(now: datetime, folder: Path, restores: Path) -> SloResult:
    from core.backup import PREFIX

    name = "Yedek"
    taken = {p.stem.removeprefix(PREFIX) for p in Path(folder).glob(f"{PREFIX}????-??-??.zip")} if Path(
        folder).exists() else set()
    sessions, started = _since(_sessions(now), date.fromisoformat(min(taken)) if taken else None)
    have = [d for d in sessions if d.isoformat() in taken]
    missing = [d for d in sessions if d.isoformat() not in taken]
    notes = [f"{len(have)}/{len(sessions)} seans günü yedekli"] + ([f"eksik: {_days(missing)}"] if missing else [])
    notes += [started] if started else []
    if not Path(restores).exists():  # the record started with v0.51.0: not measured yet, never a failure
        notes.append("geri yükleme testi sonucu henüz kaydedilmedi (haftalık test ilk çalışınca)")
        state = WARN if missing or not sessions else UNKNOWN
        return SloResult(name, state, len(have) / len(sessions) if sessions else None, "; ".join(notes))
    tests = [r for r in _rows(Path(restores)) if (t := _when(r["at"])) and now - WINDOW <= t <= now]
    if not tests:
        notes.append("son 7 günde geri yükleme testi yok")
    elif tests[-1]["ok"] != "1":
        notes.append(f"son geri yükleme testi başarısız ({_when(tests[-1]['at']):%d.%m}): {tests[-1]['detail']}")
    else:
        notes.append(f"geri yükleme testi {_when(tests[-1]['at']):%d.%m} başarılı")
    value = len(have) / len(sessions) if sessions else None
    ok = sessions and not missing and tests and tests[-1]["ok"] == "1"
    return SloResult(name, OK if ok else WARN, value, "; ".join(notes))


# --- data accuracy (second source) ---------------------------------------------------------------

ACCURACY_URL = ("https://raw.githubusercontent.com/hsnklc044-jpg/bist-ai-telegram-bot/"
                "research-results/crosscheck/latest.json")  # written by the weekly research run
ACCURACY_MAX_AGE = timedelta(days=8)


def accuracy(now: datetime, data: dict | None) -> SloResult:
    name = "Veri doğruluğu"
    if not data or not data.get("checked"):
        return SloResult(name, UNKNOWN, None, "ikinci kaynak özeti alınamadı (haftalık araştırma, crosscheck/latest.json)")
    day = date.fromisoformat(data["date"])
    if now.date() - day > ACCURACY_MAX_AGE:
        return SloResult(name, UNKNOWN, None, f"son ikinci kaynak özeti eski ({day:%d.%m})")
    differing = data.get("differing", [])
    share = len(differing) / data["checked"]
    text = f"{day:%d.%m}: {len(differing)}/{data['checked']} hisse farklı"
    if share > 0.01:
        return SloResult(name, WARN, 1 - share, f"{text}; şüpheli: {', '.join(differing)}")
    return SloResult(name, OK, 1 - share, text + (f" ({', '.join(differing)})" if differing else ""))


def fetch_accuracy(get=None) -> dict | None:
    """The latest summary from the research-results branch; None when offline (tests always are)."""

    from core.reports import health

    try:
        get = get or health._http_get or __import__("httpx").get
        response = get(ACCURACY_URL, timeout=10)
        if getattr(response, "status_code", 200) >= 400:
            return None
        return response.json()
    except Exception:  # noqa: BLE001 - unknown, never healthy
        return None


# --- quality (CI and coverage) -------------------------------------------------------------------

COVERAGE_GATE = 91  # CI fails below this (ci.yml --cov-fail-under); never lowered (CHARTER §2)
CI_API = "https://api.github.com/repos/hsnklc044-jpg/bist-ai-telegram-bot/actions/workflows/ci.yml/runs"
BRANCH = "claude/borsa-bot-creation-n7nmc9"


def quality(now: datetime, get=None) -> SloResult:
    """The latest finished CI run on the release branch: green means tests, ruff and the coverage gate passed."""

    from core.reports import health

    name = "Kalite (CI, kapsam)"
    try:
        get = get or health._http_get or __import__("httpx").get
        response = get(CI_API, params={"branch": BRANCH, "per_page": 5}, timeout=10)
        response.raise_for_status()
        runs = [r for r in response.json().get("workflow_runs", []) if r.get("status") == "completed"]
    except Exception as exc:  # noqa: BLE001 - offline: unknown, never healthy
        return SloResult(name, UNKNOWN, None, f"GitHub sorgulanamadı ({type(exc).__name__})")
    if not runs:
        return SloResult(name, UNKNOWN, None, "tamamlanmış CI çalışması yok")
    last = runs[0]
    started = datetime.fromisoformat(last["run_started_at"].replace("Z", "+00:00")).astimezone(ISTANBUL)
    text = f"son CI {started:%d.%m %H:%M} ({last.get('head_sha', '')[:7]}): {last.get('conclusion')}"
    if last.get("conclusion") != "success":
        return SloResult(name, WARN, None, text)
    return SloResult(name, OK, None, f"{text}; testler, ruff ve kapsam kapısı %{COVERAGE_GATE} geçti")


# --- record integrity -----------------------------------------------------------------------------


def integrity(now: datetime, signal_path: Path, check_personal: bool = True) -> SloResult:
    from core.signals_log import audit_log

    name = "Kayıt bütünlüğü"
    if not Path(signal_path).exists():
        return SloResult(name, UNKNOWN, None, "signal_log.csv yok")
    audit = audit_log(signal_path, now)
    start = now.date() - WINDOW + timedelta(days=1)
    missing = [d for d in audit.missing if d >= start]
    problems = []
    problems += [f"{audit.bad_rows} okunamayan satır"] if audit.bad_rows else []
    problems += [f"{audit.duplicates} tekrar kayıt"] if audit.duplicates else []
    problems += [f"kaydı olmayan seans: {_days(missing)}"] if missing else []
    problems += ["signal_log.csv boş"] if audit.empty_file else []
    if check_personal:
        from core.reports.health import CRIT, personal_files_check

        personal = personal_files_check()
        if personal.state in (WARN, CRIT):
            problems.append(personal.text)
    return SloResult(name, WARN if problems else OK, None, "; ".join(problems) or "sorun yok")


# --- all ------------------------------------------------------------------------------------------


def measure(now: datetime, folder: Path | None = None) -> list[SloResult]:
    """All objectives in TARGETS order. `folder` (tests) holds every record; None = the live files."""

    from core.reports.runs import RUNS_FILE
    from core.signals_log import SIGNAL_LOG_FILE

    if folder is None:
        from core.backup import backup_dir

        paths = dict(runs=RUNS_FILE, beats=HEARTBEATS_FILE, fresh=FRESHNESS_FILE, backups=backup_dir(),
                     restores=RESTORE_FILE, signal=SIGNAL_LOG_FILE)
    else:
        folder = Path(folder)
        paths = dict(runs=folder / "runs.csv", beats=folder / "heartbeats.csv", fresh=folder / "freshness.csv",
                     backups=folder / "backups", restores=folder / "restore_tests.csv",
                     signal=folder / "signal_log.csv")
    results = [
        report_delivery(now, paths["runs"]),
        bot_uptime(now, paths["beats"]),
        freshness(now, paths["fresh"]),
        accuracy(now, _local_json(folder / "crosscheck.json") if folder is not None else fetch_accuracy()),
        backup_slo(now, paths["backups"], paths["restores"]),
        integrity(now, paths["signal"], check_personal=folder is None),
        quality(now) if folder is None else SloResult("Kalite (CI, kapsam)", UNKNOWN, None, "testte sorgulanmaz"),
    ]
    return results


def _local_json(path: Path) -> dict | None:
    import json

    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def lines(results: list[SloResult]) -> list[str]:
    met = sum(r.state == OK for r in results)
    unknown = sum(r.state == UNKNOWN for r in results)
    head = f"📐 SLO (son 7 gün): {met}/{len(results)} hedefte, {unknown} ölçülemiyor"
    return [head, *(f"  {r.line()}" for r in results)]


__all__ = [
    "SloResult", "TARGETS", "accuracy", "quality", "backup_slo", "fetch_accuracy", "bot_uptime", "freshness", "integrity", "lines", "measure",
    "record_freshness", "record_heartbeat", "record_restore_test", "report_delivery",
]
