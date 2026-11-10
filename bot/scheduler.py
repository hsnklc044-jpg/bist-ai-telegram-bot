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
    "Model doğrulama": ("doğrulanmamış ya da süresi geçmiş bir modelin sayılarına güvenilir",
                        "docs/validation/ ve MAINTENANCE.md (yeniden doğrulama)"),
    "Makro veri": ("reel ve dolar bazlı sonuçlar eski veriyle hesaplanır",
                   "akşam raporu TCMB'den kendiliğinden tamamlar; internet bağlantısı, python -m core.market.macro"),
    "GitHub araştırması": ("haftalık araştırma sonucu yok", "GitHub Actions > Research"),
    "Bakım takvimi": ("endeks listesi ya da Python sürümü eskir; araştırma ve rapor yanlış hisseleri kullanır",
                      "docs/MAINTENANCE.md (bakım takvimi)"),
    "Dışarıdan izleme": ("bilgisayar kapalıyken ya da bot dururken kimse uyarılmaz",
                         "OPERATIONS §7; .env'deki HC_REPORT_URL ve HC_BOT_URL, internet bağlantısı"),
    "Telegram botu": ("komutlar ve 20:00 kontrolü çalışmaz",
                      "PowerShell: Start-ScheduledTask \"QuantBIST Bot\" (elle python main.py açmayın)"),
}
# severity of a KRİTİK state per check; a UYARI is one level lower
SEVERITY = {
    "Fiyat veritabanı": "KRİTİK", "Veri şeması": "KRİTİK", "Kişisel dosyalar": "KRİTİK", "Günlük rapor": "YÜKSEK", "Yedek": "YÜKSEK",
    "Canlı ölçüm kaydı": "YÜKSEK", "Telegram botu": "YÜKSEK", "Disk": "YÜKSEK", "Fiyat verisi": "ORTA",
    "Sanal hesap kaydı": "ORTA", "Tatil takvimi": "DÜŞÜK", "Makro veri": "DÜŞÜK", "Model doğrulama": "DÜŞÜK", "GitHub araştırması": "DÜŞÜK", "Dışarıdan izleme": "DÜŞÜK", "Bakım takvimi": "ORTA",
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


SIGNAL_TRACK_JOB = "signal_track"


async def signal_track_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """K-65: every hour of the session, the paper signals are followed on hourly candles."""

    from core.market.calendar import now_istanbul
    from core.signals import live

    now = now_istanbul()
    if not live.in_session(now):
        return
    lines = await _guarded(context, "saatlik takip", lambda: live.track(now.date(), strict=True))
    if lines:
        await context.bot.send_message(context.job.chat_id, "\n".join(lines))


async def _guarded(context, name: str, fn):
    """v0.99.49: transient errors retried with backoff (2, 4, 8, 16 s); when all fail, one JSON
    critical alert per job and error type in 6 hours. Never raises: the bot keeps running."""

    from core.infrastructure import retry

    try:
        return await retry.retry(fn, name=name)
    except retry.RetryExhausted as exc:
        now = now_istanbul()
        chat = getattr(getattr(context, "job", None), "chat_id", None)
        if chat and retry.should_alert(exc, now):
            await context.bot.send_message(chat, f"🚨 KRİTİK: {name} 5 denemede de çalışmadı; bot çalışmaya devam "
                                                 f"ediyor.\n{retry.payload(exc, now)}")
    except Exception:  # noqa: BLE001 - a bug: logged with its trace, the bot keeps running
        logger.exception("Job failed | %s", name)
    return None


def schedule_signal_tracking(app: Application, chat_id: int) -> bool:
    """Hourly paper-signal tracking during the session (does nothing while no book exists)."""

    if app.job_queue is None:
        return False
    app.job_queue.run_repeating(signal_track_job, interval=3600, first=120, name=SIGNAL_TRACK_JOB, chat_id=chat_id)
    return True


BACKUP_JOB = "backup_catch_up"
BACKUP_AT = time(21, 0, tzinfo=ISTANBUL)  # after the 18:30 report and the 20:00 watch


async def backup_catch_up_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """v0.99.33: a session day never ends without a backup, even when the report did not run."""

    from core import backup
    from core.market.calendar import now_istanbul

    try:
        from core.infrastructure.retry import retry

        made = await retry(lambda: backup.catch_up(now_istanbul().date()), name="yedek")
    except Exception as exc:  # noqa: BLE001 - the bot never stops on this; the user is told (K-70)
        logger.exception("Backup catch-up failed")
        text = (f"⚠️ Yedek alınamadı (21:00 kontrolü): {type(exc).__name__}: {str(exc)[:200]}. "
                "Günün yedeği yok; /durum'un Yedek satırı bunu gösterir. Diski ve OneDrive klasörünü kontrol edin.")
    else:
        if not made:
            return  # the report already took it, or no session today
        logger.info("Backup caught up by the bot | %s", made.path.name)
        text = (f"💾 Günün yedeğini 18:30 raporu almamıştı; bot 21:00'de aldı: {made.path.name} "
                f"({len(made.files)} dosya, doğrulandı). Raporun neden çalışmadığına logs/runs.csv'den bakın.")
    chat = getattr(getattr(context, "job", None), "chat_id", None)
    if chat:
        await context.bot.send_message(chat, text)


def schedule_backup_catch_up(app: Application, chat_id: int | None = None) -> bool:
    if app.job_queue is None:
        return False
    app.job_queue.run_daily(backup_catch_up_job, time=BACKUP_AT, days=WEEKDAYS, name=BACKUP_JOB,
                            job_kwargs=LATE_START, chat_id=chat_id)
    return True


HEALTH_JOB = "portfolio_health"
HEALTH_AT = time(10, 0, tzinfo=ISTANBUL)
SATURDAY = (6,)  # python-telegram-bot: 0 = Sunday


async def portfolio_health_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Road plan part 2: the weekly portfolio health report, Saturday morning."""

    from core.reports import portfolio_health

    try:
        text = await asyncio.to_thread(portfolio_health.report)
    except Exception as exc:  # noqa: BLE001 - the bot never stops on this; the user is told (K-70)
        logger.exception("Portfolio health report failed")
        text = f"⚠️ Haftalık portföy sağlık raporu hazırlanamadı: {type(exc).__name__}: {str(exc)[:200]}"
    chat = getattr(getattr(context, "job", None), "chat_id", None)
    if chat:
        await context.bot.send_message(chat, text)


def schedule_portfolio_health(app: Application, chat_id: int | None = None) -> bool:
    if app.job_queue is None:
        return False
    app.job_queue.run_daily(portfolio_health_job, time=HEALTH_AT, days=SATURDAY, name=HEALTH_JOB,
                            job_kwargs=LATE_START, chat_id=chat_id)
    return True


WEEKLY_JOB = "weekly_summary"
WEEKLY_AT = time(18, 0, tzinfo=ISTANBUL)
SUNDAY = (0,)  # python-telegram-bot: 0 = Sunday


async def weekly_summary_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Road plan part 4: the weekly operations summary (version, SLO, the latest DR drill), Sunday 18:00."""

    from core.reports import weekly

    try:
        text = await asyncio.to_thread(weekly.summary)
    except Exception as exc:  # noqa: BLE001 - the bot never stops on this; the user is told (K-70)
        logger.exception("Weekly summary failed")
        text = f"⚠️ Haftalık işletme özeti hazırlanamadı: {type(exc).__name__}: {str(exc)[:200]}"
    chat = getattr(getattr(context, "job", None), "chat_id", None)
    if chat:
        await context.bot.send_message(chat, text)
        try:  # only a message that went out counts as sent (the Monday watch reads this)
            weekly.record_sent(now_istanbul())
        except OSError:
            logger.exception("Weekly summary send record failed")


MORNING_JOB = "morning_screens"
MORNING_AT = time(9, 30, tzinfo=ISTANBUL)
WEEKDAYS = (1, 2, 3, 4, 5)  # python-telegram-bot: 0 = Sunday


async def morning_screens_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """The subscribed screens' full lists before the session opens; holidays and the locks send nothing."""

    from core.screen import subscriptions

    chat = getattr(getattr(context, "job", None), "chat_id", None)
    if not chat:
        return
    try:
        messages = await asyncio.to_thread(subscriptions.morning, now_istanbul().date())
    except Exception as exc:  # noqa: BLE001 - the bot never stops on this; the user is told
        logger.exception("Morning screens failed")
        messages = [f"⚠️ Sabah aday listesi hazırlanamadı: {type(exc).__name__}: {str(exc)[:200]}"]
    for text in messages:
        await context.bot.send_message(chat, text)


def schedule_morning_screens(app: Application, chat_id: int | None = None) -> bool:
    if app.job_queue is None:
        return False
    app.job_queue.run_daily(morning_screens_job, time=MORNING_AT, days=WEEKDAYS, name=MORNING_JOB,
                            job_kwargs={"misfire_grace_time": 1800, "coalesce": True}, chat_id=chat_id)
    return True


WEEKLY_WATCH_JOB = "weekly_summary_watch"
WEEKLY_WATCH_AT = time(9, 0, tzinfo=ISTANBUL)
MONDAY = (1,)


async def weekly_watch_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Monday 09:00: the Sunday summary was not sent -> say so (a summary cannot report its own absence)."""

    from core.reports import weekly

    try:
        text = weekly.missing_warning(now_istanbul())
    except Exception:  # noqa: BLE001
        logger.exception("Weekly summary watch failed")
        return
    chat = getattr(getattr(context, "job", None), "chat_id", None)
    if text and chat:
        await context.bot.send_message(chat, text)


def schedule_weekly_summary(app: Application, chat_id: int | None = None) -> bool:
    if app.job_queue is None:
        return False
    app.job_queue.run_daily(weekly_summary_job, time=WEEKLY_AT, days=SUNDAY, name=WEEKLY_JOB,
                            job_kwargs=LATE_START, chat_id=chat_id)
    app.job_queue.run_daily(weekly_watch_job, time=WEEKLY_WATCH_AT, days=MONDAY, name=WEEKLY_WATCH_JOB,
                            job_kwargs=LATE_START, chat_id=chat_id)
    return True


OTONOM_JOB = "otonom_summary"
OTONOM_AT = time(21, 0, tzinfo=ISTANBUL)


async def otonom_summary_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """10.11.2026: one information message a day on the autonomous development (installs, rollbacks, SLOs)."""

    from core import otonom

    try:
        text = await asyncio.to_thread(otonom.build_summary, now_istanbul())
    except Exception:  # noqa: BLE001 - a summary never stops the bot
        logger.exception("Autonomous summary failed")
        return
    chat = getattr(getattr(context, "job", None), "chat_id", None)
    if chat:
        await context.bot.send_message(chat, text)


def schedule_otonom_summary(app: Application, chat_id: int | None = None) -> bool:
    if app.job_queue is None or chat_id is None:
        return False
    app.job_queue.run_daily(otonom_summary_job, time=OTONOM_AT, name=OTONOM_JOB, job_kwargs=LATE_START,
                            chat_id=chat_id)
    return True


INBOX_JOB = "fundamentals_inbox"


async def fundamentals_inbox_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """v0.99.50: CSV files the user dropped into data/inbox/temel are imported and reported."""

    from core.fundamentals import inbox

    try:
        results = await asyncio.to_thread(inbox.process)
    except Exception:  # noqa: BLE001 - the bot never stops on this
        logger.exception("Fundamentals inbox failed")
        return
    chat = getattr(getattr(context, "job", None), "chat_id", None)
    for result in results:
        if chat:
            await context.bot.send_message(chat, inbox.message(result))


def schedule_fundamentals_inbox(app: Application, chat_id: int | None = None) -> bool:
    if app.job_queue is None:
        return False
    app.job_queue.run_repeating(fundamentals_inbox_job, interval=300, first=60, name=INBOX_JOB, chat_id=chat_id)
    return True


MACRO_JOB = "macro_refresh"


async def macro_refresh_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """v0.99.32: the USD/TRY rate no longer waits for the 18:30 report (it stuck at 23.10.2026)."""

    from core.market import macro
    from core.market.calendar import now_istanbul

    await asyncio.to_thread(macro.refresh_usd, now_istanbul().replace(tzinfo=None))


def schedule_macro_refresh(app: Application) -> bool:
    """Every hour the bot asks TCMB for the bulletins the cache is missing (none when it is complete)."""

    if app.job_queue is None:
        return False
    app.job_queue.run_repeating(macro_refresh_job, interval=3600, first=300, name=MACRO_JOB)
    return True


HEARTBEAT_JOB = "heartbeat"


async def heartbeat_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    from core.infrastructure import ping
    from core.reports.health import write_heartbeat

    await asyncio.to_thread(write_heartbeat)
    url = ping.address(ping.BOT_ENV)
    if url:  # outside monitoring (Healthchecks.io): an alarm when the bot stops, even with the PC off
        await asyncio.to_thread(ping.ping, url, name=ping.BOT_ENV)


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


__all__ = ["CATCHUP_JOB", "ENV", "report_time", "schedule_daily_report", "schedule_heartbeat", "schedule_report_watch",
           "schedule_signal_tracking"]
