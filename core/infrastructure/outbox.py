"""
QuantBIST
A copy of every outgoing Telegram message (the user's 10.11.2026 request): logs/telegram_giden.jsonl, one JSON line
per message with zaman, kaynak (bot / günlük rapor / robot özeti / güncelleyici / sağlık uyarısı), sonuc
(gönderildi / başarısız) and metin.

- Written right around the send; a failed send is recorded too.
- Token, chat_id and monitoring addresses never reach the file (scrubbed, tested).
- The file only grows. Lines older than ARCHIVE_DAYS move to a monthly archive telegram_giden_YYYY-MM.jsonl (by
  the message's month), never deleted; the archive is appended to.
- Recording never stops a message: any error here is swallowed.
"""

from __future__ import annotations

import contextvars
import json
import os
import re
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path

from core.config.paths import LOG_DIR

OUTBOX_FILE = LOG_DIR / "telegram_giden.jsonl"
ARCHIVE_DAYS = 30
SOURCES = ("bot", "günlük rapor", "robot özeti", "güncelleyici", "sağlık uyarısı")
_source: contextvars.ContextVar[str] = contextvars.ContextVar("outbox_source", default="bot")
_archived_on: date | None = None

_PATTERNS = (
    re.compile(r"https?://api\.telegram\.org/bot[^\s/]+[^\s]*"),
    re.compile(r"https?://hc-ping\.com/\S+"),
    re.compile(r"\b\d{6,12}:[A-Za-z0-9_-]{30,}\b"),  # any bot token
)


@contextmanager
def source(name: str):
    """Messages sent inside this block are recorded with `name` as their source."""

    token = _source.set(name)
    try:
        yield
    finally:
        _source.reset(token)


def current_source() -> str:
    return _source.get()


def scrub(text: str) -> str:
    out = str(text)
    for pattern in _PATTERNS:
        out = pattern.sub("[gizli]", out)
    for key in ("BOT_TOKEN", "CHAT_ID", "USER_ID", "HC_REPORT_URL", "HC_BOT_URL"):
        value = (os.environ.get(key) or "").strip()
        if len(value) >= 5:
            out = out.replace(value, "[gizli]")
    return out


def _now() -> datetime:
    from core.market.calendar import now_istanbul

    return now_istanbul()


def record(kind: str, text: str, ok: bool, now: datetime | None = None, path: Path | None = None,
           archive: bool = True) -> None:
    """Append one message; never raises."""

    try:
        when = now or _now()
        path = Path(path or OUTBOX_FILE)
        if archive:
            _archive_once(when, path)
        row = {"zaman": when.isoformat(timespec="seconds"), "kaynak": kind,
               "sonuc": "gönderildi" if ok else "başarısız", "metin": scrub(text)}
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001 - a copy must never stop the message itself
        pass


def _archive_once(now: datetime, path: Path) -> None:
    global _archived_on
    if _archived_on != now.date():
        _archived_on = now.date()
        archive(now, path)


def archive(now: datetime, path: Path | None = None) -> int:
    """Move lines older than ARCHIVE_DAYS to telegram_giden_YYYY-MM.jsonl; the number of lines moved.
    The archive is written (appended and flushed) before the main file is replaced, so a crash in between
    can only leave a line in both files, never in neither."""

    path = Path(path or OUTBOX_FILE)
    if not path.exists():
        return 0
    cutoff = now - timedelta(days=ARCHIVE_DAYS)
    keep, old = [], {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            when = datetime.fromisoformat(json.loads(line)["zaman"])
        except (ValueError, KeyError, TypeError):
            keep.append(line)  # an unreadable line stays where it is
            continue
        if when < cutoff:
            old.setdefault(f"{when:%Y-%m}", []).append(line)
        else:
            keep.append(line)
    if not old:
        return 0
    for month, lines in sorted(old.items()):
        target = path.with_name(f"{path.stem}_{month}{path.suffix}")
        with open(target, "a", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(lines) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text("".join(line + "\n" for line in keep), encoding="utf-8", newline="\n")
    os.replace(tmp, path)
    return sum(len(v) for v in old.values())


__all__ = ["ARCHIVE_DAYS", "OUTBOX_FILE", "SOURCES", "archive", "current_source", "record", "scrub", "source"]
