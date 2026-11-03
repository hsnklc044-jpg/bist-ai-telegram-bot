"""
QuantBIST
/panik and /devam (03.11.2026 request): the emergency stop of the paper signal system.

/panik cancels every paper signal waiting for a button, waiting for its entry or open (status "iptal", no result is counted) and
writes data/panic.lock. While the lock exists, nothing runs on its own and nothing new starts:
no hourly tracking, no daily signal step, no screen subscription, no new signal, no /tara. The bot
itself keeps answering /durum, /panik and /devam, so the stop can be lifted from the phone; the
lock is a file, so it survives a restart of the bot or the computer (the Windows task restarts a
stopped bot). /devam removes the lock; cancelled signals stay cancelled.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from core.config.paths import DATA_DIR, SIGNALS_DB
from core.infrastructure.logger import get_logger

logger = get_logger(__name__)

PANIC_FILE = DATA_DIR / "panic.lock"


def active(path: Path | str | None = None) -> bool:
    return Path(path or PANIC_FILE).exists()


def since(path: Path | str | None = None) -> str | None:
    path = Path(path or PANIC_FILE)
    try:
        return path.read_text(encoding="utf-8").strip() or "?" if path.exists() else None
    except OSError:
        return "?"


def trigger(day: date, lock: Path | str | None = None, book: Path | str | None = None) -> int:
    """Lock the system and cancel the open paper signals; returns how many were cancelled."""

    lock = Path(lock or PANIC_FILE)
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text(datetime.now().isoformat(timespec="seconds"), encoding="utf-8")
    book = Path(book or SIGNALS_DB)
    if not book.exists():
        return 0
    from core.signals import store

    conn = store.connect(book)
    try:
        with conn:
            cur = conn.execute("UPDATE signals SET status = 'iptal', exit_date = ?, r = NULL "
                               "WHERE status IN ('onay_bekliyor', 'bekliyor', 'acik')", (day.isoformat(),))
        logger.warning("PANIC: system locked, %d paper signals cancelled", cur.rowcount)
        return cur.rowcount
    finally:
        conn.close()


def release(lock: Path | str | None = None) -> bool:
    """Remove the lock; True when there was one."""

    lock = Path(lock or PANIC_FILE)
    if not lock.exists():
        return False
    lock.unlink()
    logger.warning("PANIC lifted")
    return True


__all__ = ["PANIC_FILE", "active", "release", "since", "trigger"]
