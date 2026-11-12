"""Ö39 (öz-denetim 10): the night job's last outcome, kept apart from the reader (which never writes files).

/durum reads it (core.reports.health.official_check); a failure or a refused file no longer shows only in the log."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from core.config.paths import LOG_DIR
from core.infrastructure.logger import get_logger

logger = get_logger(__name__)

STATE_FILE = LOG_DIR / "official_import.json"


def record_run(result=None, error: str | None = None, path: Path | None = None) -> None:
    """A quiet night (nothing read) keeps the last read and its refusals; never raises."""

    path = Path(path or STATE_FILE)
    try:
        state = read_state(path) or {}
        state["at"] = datetime.now().isoformat(timespec="seconds")
        state["error"] = error
        if result is not None and result.files:
            state["last_read"] = {"at": state["at"], "files": result.files, "rows": result.rows,
                                  "rejected": [r.split(":")[0] for r in result.rejected]}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    except (OSError, ValueError):
        logger.exception("Official import state not recorded")


def read_state(path: Path | None = None) -> dict | None:
    """None when the job never ran; OSError/ValueError when the file is unreadable."""

    path = Path(path or STATE_FILE)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
