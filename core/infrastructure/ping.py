"""
QuantBIST
Outside monitoring: a ping to Healthchecks.io (docs/OPERATIONS.md, "Dışarıdan izleme").

The outside service raises the alarm when a ping does not arrive in time, which also covers a
switched-off computer. Two addresses in .env, both secret (anyone with them can ping):

    HC_REPORT_URL   pinged after every scheduled daily report (/fail when it did not go out)
    HC_BOT_URL      pinged with the bot's 5-minute heartbeat

Without an address nothing is sent. A ping never raises, and the address is never logged.
"""

from __future__ import annotations

import os

from core.infrastructure.logger import get_logger

logger = get_logger(__name__)

REPORT_ENV = "HC_REPORT_URL"
BOT_ENV = "HC_BOT_URL"
TIMEOUT = 10
_http_get = None  # tests replace it: a test run must never reach the real monitoring service


def address(name: str) -> str:
    import core.infrastructure.settings  # noqa: F401 - loads .env into the environment

    return os.getenv(name, "").strip()


def ping(url: str, fail: bool = False, get=None) -> bool:
    """GET url (or url/fail). True when the service answered; never raises."""

    if not url:
        return False
    try:
        get = get or _http_get or __import__("httpx").get
        response = get(url.rstrip("/") + ("/fail" if fail else ""), timeout=TIMEOUT)
        return int(getattr(response, "status_code", 200)) < 400
    except Exception as exc:  # noqa: BLE001 - monitoring must never stop the report or the bot
        logger.warning("Monitoring ping failed (%s)", type(exc).__name__)
        return False


__all__ = ["BOT_ENV", "REPORT_ENV", "address", "ping"]
