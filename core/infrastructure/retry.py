"""
QuantBIST
Retry with exponential backoff and a critical alert (v0.99.49; the user's "auto-healing" request).

Transient errors (network, timeout, a locked SQLite database) are retried after 2, 4, 8 and 16
seconds: five attempts in about half a minute. Anything else is a bug and is not retried. When every
attempt fails the caller gets RetryExhausted; `payload` turns it into the JSON the user asked for
and `should_alert` lets the same job and error type reach Telegram once in 6 hours, so a long outage
is one message, not one an hour. The bot never stops on any of it.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import TypeVar

from core.config.paths import LOG_DIR
from core.infrastructure.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")
DELAYS: tuple[int, ...] = (2, 4, 8, 16)
TRANSIENT: tuple[type[BaseException], ...] = (OSError, TimeoutError, sqlite3.OperationalError)
QUIET = timedelta(hours=6)
STATE_FILE = LOG_DIR / "critical_alerts.json"


class RetryExhausted(Exception):
    def __init__(self, name: str, attempts: int, last: BaseException) -> None:
        super().__init__(f"{name}: {attempts} deneme başarısız ({type(last).__name__}: {last})")
        self.name, self.attempts, self.last = name, attempts, last


async def retry(fn: Callable[[], T], *, name: str, delays: tuple[int, ...] = DELAYS, sleep=None,
                transient: tuple[type[BaseException], ...] = TRANSIENT) -> T:
    """Run `fn` in a worker thread; retry transient errors after each delay in turn."""

    sleep = sleep or asyncio.sleep
    for attempt in range(len(delays) + 1):
        try:
            return await asyncio.to_thread(fn)
        except transient as exc:
            if attempt == len(delays):
                logger.error("Retries exhausted | %s | %s: %s", name, type(exc).__name__, exc)
                raise RetryExhausted(name, attempt + 1, exc) from exc
            logger.warning("Transient failure, retry in %d s | %s | %s: %s", delays[attempt], name,
                           type(exc).__name__, exc)
            await sleep(delays[attempt])
    raise AssertionError("unreachable")  # pragma: no cover


def payload(exc: RetryExhausted, now: datetime) -> str:
    return json.dumps({"seviye": "KRİTİK", "is": exc.name, "deneme": exc.attempts,
                       "hata": f"{type(exc.last).__name__}: {str(exc.last)[:200]}",
                       "zaman": now.replace(microsecond=0, tzinfo=None).isoformat()}, ensure_ascii=False)


def should_alert(exc: RetryExhausted, now: datetime, state: Path | None = None) -> bool:
    """The same job and error type alerts once per QUIET period; the state survives restarts."""

    path = Path(state or STATE_FILE)
    key = f"{exc.name}|{type(exc.last).__name__}"
    try:
        seen = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (OSError, ValueError):
        seen = {}
    last = seen.get(key)
    naive = now.replace(tzinfo=None)
    if last and naive - datetime.fromisoformat(last) < QUIET:
        return False
    seen[key] = naive.isoformat()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(seen, ensure_ascii=False), encoding="utf-8")
    except OSError:
        logger.warning("Critical alert state could not be saved")
    return True


__all__ = ["DELAYS", "RetryExhausted", "TRANSIENT", "payload", "retry", "should_alert"]
