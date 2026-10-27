"""
QuantBIST
In-bot daily report, for servers.

On a server the bot itself sends the after-close report, so one process
owns data/ (no second program writing the ledger at the same time).
It is off unless DAILY_REPORT_AT is set, because on a Windows PC the
scheduled task (scripts/register_daily_task.ps1) already sends it and
the report would arrive twice. If both are on anyway, the report lock
and logs/runs.csv (core/reports/runs.py) keep it to one run and one
message per data day.

    DAILY_REPORT_AT=18:30     # Istanbul time, weekdays
"""

from __future__ import annotations

import asyncio
import os
from datetime import time

from telegram.ext import Application, ContextTypes

from core.infrastructure.logger import get_logger
from core.market.calendar import ISTANBUL, now_istanbul

logger = get_logger(__name__)

ENV = "DAILY_REPORT_AT"
WEEKDAYS = (1, 2, 3, 4, 5)  # python-telegram-bot: 0 = Sunday
JOB_NAME = "daily_report"
CATCHUP_JOB = "daily_report_catchup"
CATCHUP_AFTER = 60  # seconds after start: a restart after 18:30 still sends the missed report

# After the report should have gone out (by either scheduler), check the
# run log and tell the user if it did not. Silent when everything is fine.
WATCH_AT = time(20, 0, tzinfo=ISTANBUL)
WATCH_JOB = "report_watch"

# python-telegram-bot lets a job start at most 1 second late; after sleep or a late internet the
# day's run was skipped silently. A daily job may now start up to 4 hours late, once.
LATE_START = {"misfire_grace_time": 4 * 3600, "coalesce": True}


def report_time(raw: str | None = None) -> time | None:
    """DAILY_REPORT_AT as an Istanbul time; None when unset."""

    raw = (os.getenv(ENV, "") if raw is None else raw).strip()

    if not raw:
        return None

    try:
        hour, minute = (int(part) for part in raw.split(":"))
        return time(hour, minute, tzinfo=ISTANBUL)
    except ValueError as exc:
        raise ValueError(f"{ENV} must look like 18:30, got {raw!r}.") from exc


async def daily_report_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    from core.reports import daily

    code = await asyncio.to_thread(daily.main, ["--send", "--log-dir", "logs"])

    if code:
        logger.error("Scheduled daily report failed; see logs/daily_<date>.log")


def schedule_daily_report(app: Application, at: time | None = None) -> bool:
    """Register the weekday job. Returns False when it stays off."""

    at = at or report_time()

    if at is None:
        return False

    if app.job_queue is None:
        logger.warning(
            "%s is set but the JobQueue is missing; install python-telegram-bot[job-queue].",
            ENV,
        )
        return False

    app.job_queue.run_daily(daily_report_job, time=at, days=WEEKDAYS, name=JOB_NAME, job_kwargs=LATE_START)
    # like the Windows task's StartWhenAvailable: one run at start; it sends nothing when the
    # latest data day already went out, and is held off by the lock if a report is running
    app.job_queue.run_once(daily_report_job, when=CATCHUP_AFTER, name=CATCHUP_JOB)
    logger.info("Daily report scheduled for %s (Istanbul), weekdays.", at.strftime("%H:%M"))

    return True


# what a problem means for the user and what to do, per check
GUIDANCE = {
    "Günlük rapor": ("günün raporu ve canlı ölçüm kaydı eksik kalır",
                     "bilgisayar açık mı, Windows görevi çalıştı mı: logs/runs.csv ve logs/daily_<tarih>.log"),
    "Fiyat verisi": ("rapor ve uyarılar eski fiyatlarla hesaplanır", "internet bağlantısı; ertesi gün kendiliğinden düzelir"),
    "Fiyat veritabanı": ("fiyatlar okunamayabilir", "botu durdurup son market.db yedeğini geri yükleyin"),
    "Canlı ölçüm kaydı": ("canlı ölçümün örneklemi bozulur", "/performans 'Kayıt sağlığı' satırına bakın"),
    "Sanal hesap kaydı": ("sanal hesap izlenemez", "data/equity_log.csv dosyasını kontrol edin"),
    "Veri şeması": ("kayıtlar bu sürümle okunamaz", "güncellemeyi geri alın; dosyaları değiştirmeyin"),
    "Kişisel dosyalar": ("portföy, emir veya takip listesi hesaplanamaz; dosyaya dokunulmaz",
                         "mesajdaki satırı düzeltin ya da python -m core.backup --list ile yedekten geri yükleyin"),
    "Yedek": ("bir arızada kişisel kayıtlar kaybolabilir", "python -m core.backup ve BACKUP_DIR klasörü"),
    "Disk": ("yedek ve kayıtlar yazılamayabilir", "diskte yer açın"),
    "Tatil takvimi": ("tatil günleri eksik rapor sayılabilir", "data/bist_holidays.csv'yi güncelleyin"),
    "GitHub araştırması": ("haftalık araştırma sonucu yok", "GitHub Actions > Research"),
    "Telegram botu": ("komutlar ve 20:00 kontrolü çalışmaz",
                      "PowerShell: Start-ScheduledTask \"QuantBIST Bot\" (elle python main.py açmayın)"),
}
# severity of a KRİTİK state per check; a UYARI is one level lower
SEVERITY = {
    "Fiyat veritabanı": "KRİTİK", "Veri şeması": "KRİTİK", "Kişisel dosyalar": "KRİTİK", "Günlük rapor": "YÜKSEK", "Yedek": "YÜKSEK",
    "Canlı ölçüm kaydı": "YÜKSEK", "Telegram botu": "YÜKSEK", "Disk": "YÜKSEK", "Fiyat verisi": "ORTA",
    "Sanal hesap kaydı": "ORTA", "Tatil takvimi": "DÜŞÜK", "GitHub araştırması": "DÜŞÜK",
}
LEVELS = ["KRİTİK", "YÜKSEK", "ORTA", "DÜŞÜK"]


def severity(check) -> str:
    from core.reports.health import CRIT

    level = SEVERITY.get(check.name, "ORTA")
    if check.state != CRIT:
        level = LEVELS[min(LEVELS.index(level) + 1, len(LEVELS) - 1)]
    return level


ALERT_STATE = "alerts_sent.json"
ALERT_ON_UNKNOWN = {"Günlük rapor"}  # an unverifiable report is a problem; other unknowns only show in /durum
REPEAT_AFTER_DAYS = 3


def _alert_text(check, now) -> str:
    from core.reports.health import LABELS

    impact, action = GUIDANCE.get(check.name, ("", "/durum"))
    return (
        f"{check.state} {LABELS[check.state]} · {check.name} · önem: {severity(check)}\n"
        f"Tespit: {now:%d.%m.%Y %H:%M} · {check.text}\n"
        f"Etkisi: {impact}\n"
        f"Otomatik işlem: yok (bot yalnızca bildirir)\n"
        f"Yapılacak: {action}"
    )


def due_alerts(checks, now, state_path) -> list:
    """Problems to send now: new ones, or ones last sent REPEAT_AFTER_DAYS or more ago."""

    import json
    from pathlib import Path

    from core.reports.health import CRIT, UNKNOWN, WARN

    path = Path(state_path)
    try:
        sent = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (OSError, ValueError):
        sent = {}
    due = []
    for check in checks:
        if check.state not in (CRIT, WARN) and not (check.state == UNKNOWN and check.name in ALERT_ON_UNKNOWN):
            continue
        key = f"{check.name}|{check.state}"
        last = sent.get(key)
        if last is None or (now.date() - __import__("datetime").date.fromisoformat(last)).days >= REPEAT_AFTER_DAYS:
            due.append(check)
            sent[key] = now.date().isoformat()
    # a solved problem may alert again as soon as it comes back
    current = {f"{c.name}|{c.state}" for c in checks}
    sent = {k: v for k, v in sent.items() if k in current}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sent, indent=1), encoding="utf-8")
    return due


async def report_watch_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Weekday 20:00: all health checks; each problem is sent once, repeated only after 3 days."""

    from core.config.paths import LOG_DIR
    from core.reports.health import health_checks

    now = now_istanbul()
    checks = await asyncio.to_thread(health_checks, now)
    for check in due_alerts(checks, now, LOG_DIR / ALERT_STATE):
        logger.warning("Health watch: %s | %s", check.name, check.text)
        await context.bot.send_message(context.job.chat_id, _alert_text(check, now))


HEARTBEAT_JOB = "heartbeat"


async def heartbeat_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    from core.infrastructure import ping
    from core.reports.health import write_heartbeat

    await asyncio.to_thread(write_heartbeat)
    url = ping.address(ping.BOT_ENV)
    if url:  # outside monitoring (Healthchecks.io): an alarm when the bot stops, even with the PC off
        await asyncio.to_thread(ping.ping, url)


def schedule_heartbeat(app: Application) -> bool:
    """Every 5 minutes the bot writes logs/heartbeat.txt; the daily report checks it."""

    if app.job_queue is None:
        return False
    app.job_queue.run_repeating(heartbeat_job, interval=300, first=5, name=HEARTBEAT_JOB)
    return True


def schedule_report_watch(app: Application, chat_id: int) -> bool:
    """Weekday 20:00 check that today's report went out."""

    if app.job_queue is None:
        return False

    app.job_queue.run_daily(report_watch_job, time=WATCH_AT, days=WEEKDAYS, name=WATCH_JOB, chat_id=chat_id,
                            job_kwargs=LATE_START)
    return True


__all__ = ["CATCHUP_JOB", "ENV", "report_time", "schedule_daily_report", "schedule_heartbeat", "schedule_report_watch"]
