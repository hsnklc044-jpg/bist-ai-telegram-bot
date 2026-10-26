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

# After the report should have gone out (by either scheduler), check the
# run log and tell the user if it did not. Silent when everything is fine.
WATCH_AT = time(20, 0, tzinfo=ISTANBUL)
WATCH_JOB = "report_watch"


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

    app.job_queue.run_daily(daily_report_job, time=at, days=WEEKDAYS, name=JOB_NAME)
    logger.info("Daily report scheduled for %s (Istanbul), weekdays.", at.strftime("%H:%M"))

    return True


async def report_watch_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    from core.reports.health import OK, report_check

    check = await asyncio.to_thread(report_check, now_istanbul())

    if check.state != OK:
        logger.warning("Report watch: %s", check.text)
        await context.bot.send_message(
            context.job.chat_id, f"{check.line()}\nAyrıntı: /durum, logs/runs.csv, logs/daily_<tarih>.log"
        )


def schedule_report_watch(app: Application, chat_id: int) -> bool:
    """Weekday 20:00 check that today's report went out."""

    if app.job_queue is None:
        return False

    app.job_queue.run_daily(report_watch_job, time=WATCH_AT, days=WEEKDAYS, name=WATCH_JOB, chat_id=chat_id)
    return True


__all__ = ["ENV", "report_time", "schedule_daily_report", "schedule_report_watch"]
