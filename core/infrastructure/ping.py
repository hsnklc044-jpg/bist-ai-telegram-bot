"""
QuantBIST
Outside monitoring: a ping to Healthchecks.io (docs/OPERATIONS.md, "Dışarıdan izleme").

The outside service raises the alarm when a ping does not arrive in time, which also covers a
switched-off computer. Two addresses in .env, both secret (anyone with them can ping):

    HC_REPORT_URL   pinged after every scheduled daily report (/fail when it did not go out)
    HC_BOT_URL      pinged with the bot's 5-minute heartbeat

Without an address nothing is sent. A ping never raises, and the address is never logged.
With `name`, the outcome (time, delivered, /fail or not; never the address) is kept in
logs/monitoring.json for /durum.
"""

from __future__ import annotations

import json
import os

from core.config.paths import LOG_DIR
from core.infrastructure.logger import get_logger

logger = get_logger(__name__)

REPORT_ENV = "HC_REPORT_URL"
BOT_ENV = "HC_BOT_URL"
TIMEOUT = 10
STATE_FILE = LOG_DIR / "monitoring.json"
_http_get = None  # tests replace it: a test run must never reach the real monitoring service


def address(name: str) -> str:
    import core.infrastructure.settings  # noqa: F401 - loads .env into the environment

    return os.getenv(name, "").strip()


def ping(url: str, fail: bool = False, get=None, name: str | None = None, state_path=None, now=None) -> bool:
    """GET url (or url/fail). True when the service answered; never raises."""

    if not url:
        return False
    try:
        get = get or _http_get or __import__("httpx").get
        response = get(url.rstrip("/") + ("/fail" if fail else ""), timeout=TIMEOUT)
        ok = int(getattr(response, "status_code", 200)) < 400
    except Exception as exc:  # noqa: BLE001 - monitoring must never stop the report or the bot
        logger.warning("Monitoring ping failed (%s)", type(exc).__name__)
        ok = False
    if name:
        _record(name, ok, fail, state_path, now)
    return ok


def last_pings(state_path=None) -> dict:
    """{env name: {"at": iso time, "ok": delivered, "fail": sent as /fail}}; {} when unknown."""

    from pathlib import Path

    try:
        return json.loads(Path(state_path or STATE_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _record(name: str, ok: bool, fail: bool, state_path=None, now=None) -> None:
    from pathlib import Path

    from core.market.calendar import now_istanbul

    path = Path(state_path or STATE_FILE)
    try:
        state = last_pings(path)
        state[name] = {"at": (now or now_istanbul()).isoformat(timespec="seconds"), "ok": ok, "fail": fail}
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=1), encoding="utf-8")
        tmp.replace(path)
    except OSError as exc:  # recording is for /durum only; never stops anything
        logger.warning("Monitoring state not saved (%s)", type(exc).__name__)


def main(argv: list[str] | None = None) -> int:
    """Alarm drill (MATURITY S2): --drill marks "QuantBIST rapor" as failed so the alert must reach you;
    --recover puts it back. The address is never printed."""

    import argparse

    from core.infrastructure.console import utf8_output

    utf8_output()
    parser = argparse.ArgumentParser(description="Healthchecks alarm drill")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--drill", action="store_true", help="send /fail to the report check (a real alarm)")
    group.add_argument("--recover", action="store_true", help="send success to the report check")
    args = parser.parse_args(argv)

    url = address(REPORT_ENV)
    if not url:
        print("HC_REPORT_URL .env'de yok: önce izlemeyi kurun (OPERATIONS §7). Hiçbir şey gönderilmedi.")
        return 1
    if not ping(url, fail=args.drill, name=REPORT_ENV):
        print("Servise ulaşılamadı; internet bağlantısını kontrol edip tekrar deneyin.")
        return 1
    if args.drill:
        print('Gönderildi: "QuantBIST rapor" kontrolü şimdi DOWN. 1-2 dakika içinde Telegram/e-posta alarmı gelmeli.\n'
              "Alarm geldiyse tatbikat başarılı. Kontrolü geri almak için: python -m core.infrastructure.ping --recover")
    else:
        print('Gönderildi: "QuantBIST rapor" kontrolü yeniden UP; "geri geldi" bildirimi de gelmeli.')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["BOT_ENV", "REPORT_ENV", "STATE_FILE", "address", "last_pings", "main", "ping"]
