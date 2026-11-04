"""
QuantBIST
Fundamentals inbox (v0.99.50, DECISIONS K-70 madde 6): the user's "watcher ETL", done without a
file watcher (Windows file locks and half-copied files make watchers fragile).

The user downloads a report from KAP by hand, turns it into the CSV that `core.fundamentals.store`
accepts and drops it into data/inbox/temel/. Every few minutes the bot:
- leaves a file younger than SETTLE seconds alone (it may still be copying);
- imports it with the existing checked import (append-only, a known row is never added twice);
- moves it to islendi/ (something was read) or reddedildi/ (nothing could be read; the reason goes
  next to it as <name>.hata.txt), never overwriting an earlier file of the same name;
- tells the user what happened.

There is no network code here: KAP's terms for automated fetching are not confirmed (K-48).
"""

from __future__ import annotations

import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from core.config.paths import DATA_DIR
from core.infrastructure.logger import get_logger

logger = get_logger(__name__)

INBOX = DATA_DIR / "inbox" / "temel"
SETTLE = 60  # seconds a file must be left unchanged before it is read


@dataclass
class Result:
    name: str
    added: int
    rejected: list[str] = field(default_factory=list)
    moved_to: Path | None = None
    error: str = ""


def _target(folder: Path, name: str, now: datetime) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    stem, suffix = Path(name).stem, Path(name).suffix
    path = folder / f"{now:%Y%m%d-%H%M%S}_{stem}{suffix}"
    n = 1
    while path.exists():
        path = folder / f"{now:%Y%m%d-%H%M%S}_{stem}_{n}{suffix}"
        n += 1
    return path


def process(inbox: Path | None = None, store_path: Path | None = None, now: datetime | None = None
            ) -> list[Result]:
    from core.fundamentals import store

    inbox = Path(inbox or INBOX)
    if not inbox.is_dir():
        return []
    now = now or datetime.now()
    results = []
    for path in sorted(inbox.glob("*.csv")):
        try:
            if time.time() - path.stat().st_mtime < SETTLE:
                continue
        except OSError:
            continue
        result = Result(path.name, 0)
        try:
            result.added, result.rejected = store.import_file(path, store_path, now)
        except Exception as exc:  # noqa: BLE001 - a bad file is reported and set aside, never fatal
            logger.warning("Fundamentals file unreadable | %s | %s", path.name, exc)
            result.error = f"{type(exc).__name__}: {exc}"
        readable = not result.error and (result.added or not result.rejected)
        try:
            result.moved_to = _target(inbox / ("islendi" if readable else "reddedildi"), path.name, now)
            shutil.move(str(path), result.moved_to)
            if not readable:
                reasons = [result.error] if result.error else result.rejected
                result.moved_to.with_suffix(".hata.txt").write_text("\n".join(reasons) + "\n", encoding="utf-8")
        except OSError as exc:
            logger.warning("Fundamentals file could not be moved | %s | %s", path.name, exc)
            result.error = result.error or f"taşınamadı: {exc}"
        results.append(result)
    return results


def message(r: Result) -> str:
    if r.error:
        return f"📥 Temel veri: {r.name} okunamadı ({r.error}); dosya reddedildi/ klasöründe."
    text = f"📥 Temel veri: {r.name}: {r.added} satır eklendi"
    if r.rejected:
        text += f", {len(r.rejected)} satır reddedildi (ilki: {r.rejected[0]})"
        if not r.added:
            text += "; dosya reddedildi/ klasöründe, nedenler yanındaki .hata.txt dosyasında"
    return text + "."


__all__ = ["INBOX", "Result", "message", "process"]
