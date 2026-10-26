"""
QuantBIST
One daily report at a time, and one Telegram report per data day.

Two schedulers (the Windows task and DAILY_REPORT_AT in the bot) or a
/report pressed at 18:30 could otherwise run the report together: both
would read and rewrite paper_orders.csv and ledger.csv, and a pending
paper order could be filled twice.

- report_lock(): an exclusive lock file in data/; a second run waits for
  nothing and is told the report is busy. A lock left behind by a run that
  was killed (computer switched off) expires after STALE_AFTER.
- logs/runs.csv: one row per run (started, finished, data day, status),
  the evidence that the report went out. A data day already sent is not
  sent again, so a holiday (no new candle) does not repeat yesterday.
"""

from __future__ import annotations

import csv
import os
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from core.config.paths import DATA_DIR, LOG_DIR
from core.infrastructure.logger import get_logger
from core.market.calendar import now_istanbul

logger = get_logger(__name__)

LOCK_FILE = DATA_DIR / ".daily.lock"
RUNS_FILE = LOG_DIR / "runs.csv"
STALE_AFTER = timedelta(hours=1)
FIELDS = ("started_at", "finished_at", "data_day", "status", "detail")

SENT = "sent"


class ReportBusy(RuntimeError):
    """Another daily report run holds the lock."""


@contextmanager
def report_lock(path: Path | str | None = None, now: datetime | None = None):
    path = Path(path or LOCK_FILE)
    now = now or now_istanbul()
    path.parent.mkdir(parents=True, exist_ok=True)

    for attempt in range(2):
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            age = now.timestamp() - path.stat().st_mtime
            if attempt == 0 and age > STALE_AFTER.total_seconds():
                logger.warning("Removing stale report lock (%.0f min old)", age / 60)
                path.unlink(missing_ok=True)
                continue
            raise ReportBusy(f"Rapor şu an başka bir çalıştırmada hazırlanıyor ({path.name}).") from None

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(f"{os.getpid()} {now.isoformat(timespec='seconds')}\n")
        yield
    finally:
        path.unlink(missing_ok=True)


@dataclass
class Run:
    started_at: str
    finished_at: str
    data_day: str
    status: str
    detail: str = ""


def read_runs(path: Path | str | None = None) -> list[Run]:
    path = Path(path or RUNS_FILE)
    if not path.exists():
        return []
    with open(path, encoding="utf-8", newline="") as fh:
        return [Run(**{k: r.get(k) or "" for k in FIELDS}) for r in csv.DictReader(fh)]


def already_sent(day: date, path: Path | str | None = None) -> bool:
    return any(r.status == SENT and r.data_day == day.isoformat() for r in read_runs(path))


def record_run(
    started: datetime,
    status: str,
    day: date | None = None,
    detail: str = "",
    path: Path | str | None = None,
    now: datetime | None = None,
) -> None:
    """Append one row; recording must never break the report."""

    path = Path(path or RUNS_FILE)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        new = not path.exists()
        with open(path, "a", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, FIELDS, lineterminator="\n")
            if new:
                writer.writeheader()
            writer.writerow({
                "started_at": started.isoformat(timespec="seconds"),
                "finished_at": (now or now_istanbul()).isoformat(timespec="seconds"),
                "data_day": day.isoformat() if day else "",
                "status": status,
                "detail": detail.replace("\n", " ")[:300],
            })
    except OSError:
        logger.exception("Run could not be recorded")


__all__ = ["ReportBusy", "Run", "already_sent", "read_runs", "record_run", "report_lock"]
