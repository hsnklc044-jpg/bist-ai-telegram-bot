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


def _last_close(bars, symbol: str) -> float | None:
    try:
        df = bars(symbol)
    except Exception:  # noqa: BLE001 - no price: the position is left open, never erased
        return None
    if df is None or df.empty:
        return None
    price = float(df["close"].iloc[-1])
    return price if price > 0 else None


def trigger(day: date, lock: Path | str | None = None, book: Path | str | None = None, bars=None) -> int:
    """Lock the system; cancel the cards and waiting signals; close the open positions at their last
    close and count the result (v0.99.52: they used to be cancelled and their loss erased, M32-2).
    An open position without a price stays open. Returns how many signals were cancelled or closed."""

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
                               "WHERE status IN ('onay_bekliyor', 'bekliyor')", (day.isoformat(),))
        done = cur.rowcount
        open_ = store.signals(conn, ("acik",))
        if open_ and bars is None:
            from core.reports.daily import adjusted_bars as bars
        for s in open_:
            price = _last_close(bars, s.symbol) if s.entry_price else None
            if price is None:
                logger.warning("PANIC: no price for %s; the position stays open", s.symbol)
                continue
            with conn:
                conn.execute("UPDATE signals SET status = 'panik', exit_date = ?, exit_price = ?, r = ? WHERE id = ?",
                             (day.isoformat(), price, price / s.entry_price - 1 - store.COST, s.id))
            done += 1
        logger.warning("PANIC: system locked, %d paper signals cancelled or closed", done)
        return done
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
