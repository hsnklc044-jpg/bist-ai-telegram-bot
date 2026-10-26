"""
QuantBIST
System health (/durum): is the daily chain actually working?

Every line is read from evidence on disk: logs/runs.csv, the price
store, data/signal_log.csv, data/equity_log.csv and the backup folder.
A check that cannot be made says "bilinmiyor" (unknown), never OK.

The Windows scheduled task itself is not visible from here; its work
shows up in logs/runs.csv.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from core import __version__
from core.config.paths import EQUITY_LOG_FILE, SIGNAL_LOG_FILE
from core.market.calendar import (
    ISTANBUL,
    SESSION_FINAL,
    covered_until,
    holidays,
    last_final_session_date,
    now_istanbul,
    sessions_between,
)
from core.market.universe import BENCHMARK
from core.reports import runs as run_log
from core.reports.daily import adjusted_bars, tr

OK, WARN, UNKNOWN = "✅", "⚠️", "❔"

# the scheduled report runs at 18:30; a session counts as due once this
# much time has passed after its candle became final
REPORT_GRACE = timedelta(hours=1, minutes=15)
BACKUP_MAX_AGE = timedelta(days=4)


@dataclass
class Check:
    name: str
    state: str
    text: str

    def line(self) -> str:
        return f"{self.state} {self.name}: {self.text}"


def _date(day: date) -> str:
    return day.strftime("%d.%m.%Y")


def _session_start(day: date) -> datetime:
    return datetime.combine(day, SESSION_FINAL, tzinfo=ISTANBUL)


def due_session(now: datetime) -> date:
    """The latest session whose daily report should already have gone out."""

    return last_final_session_date(now - REPORT_GRACE)


def report_check(now: datetime, path: Path | str | None = None) -> Check:
    rows = run_log.read_runs(path)
    done = [r for r in rows if r.status in (run_log.SENT, "skipped", "holiday")]
    sent = [r for r in rows if r.status == run_log.SENT]

    if not done:
        return Check("Günlük rapor", UNKNOWN, "henüz gönderim kaydı yok (kayıt v0.22.0 ile başladı)")

    last = sent[-1] if sent else None
    text = (
        f"son gönderilen {_date(date.fromisoformat(last.data_day))} kapanışı "
        f"({datetime.fromisoformat(last.started_at):%d.%m %H:%M})"
        if last
        else "gönderilmiş rapor yok"
    )

    due = due_session(now)
    covered = any(datetime.fromisoformat(r.started_at) >= _session_start(due) for r in done)
    failed = [r for r in rows if r.status == "failed"]
    if failed and (not done or failed[-1].started_at > done[-1].started_at):
        return Check("Günlük rapor", WARN, f"{text}; son çalıştırma hata verdi: {failed[-1].detail}")
    stale = [r for r in rows if r.status == "stale" and datetime.fromisoformat(r.started_at) >= _session_start(due)]
    if not covered and stale:
        return Check("Günlük rapor", WARN, f"{text}; {_date(due)} kapanış verisi gelmedi ({stale[-1].detail})")
    if not covered:
        return Check("Günlük rapor", WARN, f"{text}; {_date(due)} kapanış raporu gitmedi")

    return Check("Günlük rapor", OK, text)


def price_check(now: datetime, bars=adjusted_bars) -> Check:
    try:
        bench = bars(BENCHMARK)
    except Exception as exc:  # noqa: BLE001 - shown as unknown, never as OK
        return Check("Fiyat verisi", UNKNOWN, f"okunamadı ({type(exc).__name__})")

    if bench.empty:
        return Check("Fiyat verisi", UNKNOWN, "XU100 verisi yok")

    last = bench.index[-1].date()
    expected = last_final_session_date(now)
    behind = sessions_between(last, expected)

    if behind <= 0:
        return Check("Fiyat verisi", OK, f"XU100 son kapanış {_date(last)}")
    return Check("Fiyat verisi", WARN, f"XU100 son kapanış {_date(last)}; {behind} seans geride")


def calendar_check(now: datetime) -> Check:
    until = covered_until()
    upcoming = [h for d, h in sorted(holidays().items()) if now.date() <= d <= now.date() + timedelta(days=14)]
    soon = "; yaklaşan: " + ", ".join(
        f"{h.day:%d.%m} {h.name}{' (yarım gün)' if h.kind == 'half' else ''}" for h in upcoming
    ) if upcoming else ""

    if until is None or until < now.year:
        return Check("Tatil takvimi", UNKNOWN, f"{now.year} yılı tatilleri data/bist_holidays.csv'de yok")
    if until == now.year and now.month == 12:
        return Check("Tatil takvimi", WARN, f"{until + 1} tatilleri henüz eklenmedi{soon}")
    return Check("Tatil takvimi", OK, f"{until} sonuna kadar{soon}")


def signal_check(path: Path | str | None = None) -> Check:
    path = Path(path or SIGNAL_LOG_FILE)
    if not path.exists():
        return Check("Canlı ölçüm kaydı", UNKNOWN, "signal_log.csv yok")

    try:
        with open(path, encoding="utf-8", newline="") as fh:
            rows = [r for r in csv.DictReader(fh) if r.get("source") == "daily"]
    except (OSError, csv.Error) as exc:
        return Check("Canlı ölçüm kaydı", WARN, f"okunamadı ({exc})")

    if not rows:
        return Check("Canlı ölçüm kaydı", UNKNOWN, "günlük kayıt yok")

    keys = [(r["symbol"], r["data_date"]) for r in rows]
    days = sorted({d for _, d in keys})
    duplicates = len(keys) - len(set(keys))
    text = f"{len(days)} gün, {len(rows)} kayıt; son veri {_date(date.fromisoformat(days[-1]))}"

    if duplicates:
        return Check("Canlı ölçüm kaydı", WARN, f"{text}; {duplicates} tekrar kayıt")
    return Check("Canlı ölçüm kaydı", OK, text)


def equity_check(path: Path | str | None = None) -> Check:
    path = Path(path or EQUITY_LOG_FILE)
    if not path.exists():
        return Check("Sanal hesap kaydı", UNKNOWN, "equity_log.csv yok")

    try:
        df = pd.read_csv(path)
        paper = df[df["account"] == "paper"]
        last = paper.iloc[-1]
    except Exception as exc:  # noqa: BLE001 - shown as a problem, never as OK
        return Check("Sanal hesap kaydı", WARN, f"okunamadı ({type(exc).__name__})")

    return Check(
        "Sanal hesap kaydı", OK, f"{_date(date.fromisoformat(last['date']))}: {tr(float(last['value']))} TL"
    )


def backup_check(now: datetime, target: Path | None = None) -> Check:
    from core.backup import backup_dir, list_backups

    target = Path(target or backup_dir())
    try:
        backups = list_backups(target)
    except OSError as exc:
        return Check("Yedek", UNKNOWN, f"klasör okunamadı ({exc})")

    if not backups:
        return Check("Yedek", UNKNOWN, f"yedek yok ({target})")

    last = backups[-1]
    taken = datetime.fromtimestamp(last.stat().st_mtime, tz=ISTANBUL)
    text = f"{last.name} ({taken:%d.%m %H:%M})"

    if now - taken > BACKUP_MAX_AGE:
        return Check("Yedek", WARN, f"{text}; {(now - taken).days} gündür yeni yedek yok")
    return Check("Yedek", OK, text)


def health_checks(now: datetime | None = None, bars=adjusted_bars) -> list[Check]:
    now = now or now_istanbul()
    return [
        report_check(now),
        price_check(now, bars),
        signal_check(),
        equity_check(),
        backup_check(now),
        calendar_check(now),
    ]


def health_report(now: datetime | None = None, bars=adjusted_bars) -> str:
    now = now or now_istanbul()
    checks = health_checks(now, bars)
    states = {c.state for c in checks}

    if WARN in states:
        verdict = f"{WARN} Dikkat gereken bileşen var"
    elif UNKNOWN in states:
        verdict = f"{UNKNOWN} Bazı bileşenler doğrulanamadı"
    else:
        verdict = f"{OK} Tüm kontroller geçti"

    return "\n".join([
        f"🩺 QuantBIST v{__version__} durum – {now:%d.%m.%Y %H:%M}",
        verdict,
        "",
        *(c.line() for c in checks),
        "",
        "Windows görevi buradan görülemez; çalışması logs/runs.csv kayıtlarından izlenir.",
    ])


__all__ = ["Check", "due_session", "health_checks", "health_report"]
