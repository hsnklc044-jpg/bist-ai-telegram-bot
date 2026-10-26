"""
Snapshot of folders that tests must not touch (the real data/ and logs/).

A file counts as changed when its size, modification time or content
differs; content is compared by SHA-256 up to HASH_LIMIT bytes, so a
rewrite with the same size and time is still caught. Larger files
(the price store) are compared by size and time only.

Files the running bot writes on its own (heartbeat, log, report runs)
change while the tests run on the user's PC, so outside CI they are
ignored. On CI nothing else runs, and every file counts.
"""

from __future__ import annotations

import fnmatch
import hashlib
import os
from pathlib import Path

HASH_LIMIT = 50_000_000
LIVE_FILES = ("heartbeat.txt", "quantbist.log*", "runs.csv", "daily_*.log", "alerts_sent.json", ".daily.lock",
              "setup_report.txt", "verify_report.txt", "verify_part.txt", "market.db*", "backups")


def _live(path: Path, root: Path) -> bool:
    parts = path.relative_to(root).parts
    return any(fnmatch.fnmatch(part, pattern) for part in parts for pattern in LIVE_FILES)


def _state(path: Path) -> tuple:
    stat = path.stat()
    digest = hashlib.sha256(path.read_bytes()).hexdigest() if stat.st_size <= HASH_LIMIT else ""
    return stat.st_size, stat.st_mtime_ns, digest


def snapshot(folders, strict: bool | None = None) -> dict[str, tuple]:
    strict = bool(os.environ.get("CI")) if strict is None else strict
    state = {}
    for folder in folders:
        folder = Path(folder)
        if not folder.exists():
            continue
        for path in folder.rglob("*"):
            if path.is_dir() or (not strict and _live(path, folder)):
                continue
            try:
                state[str(path)] = _state(path)
            except OSError:
                continue  # removed while scanning (another process)
    return state


def changes(before: dict[str, tuple], after: dict[str, tuple]) -> list[str]:
    out = [f"oluşturuldu: {p}" for p in sorted(after.keys() - before.keys())]
    out += [f"değişti: {p}" for p in sorted(before.keys() & after.keys()) if before[p] != after[p]]
    out += [f"silindi: {p}" for p in sorted(before.keys() - after.keys())]
    return out
