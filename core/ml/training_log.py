"""
QuantBIST
A record of every live /tara ai model training (logs/model_egitim.csv, private, append-only).

Two trainers call signal_filter.fit_live: the Friday refit after the daily report and /tara ai when the
saved model is missing or older than MAX_MODEL_AGE. Each writes one row, so a card can be tied to the
model that scored it. Writing the row never stops a training.
"""

from __future__ import annotations

import csv
import logging
from datetime import date, datetime

from core.config.paths import LOG_DIR

logger = logging.getLogger(__name__)

LOG_FILE = LOG_DIR / "model_egitim.csv"
HEADER = ["zaman", "gun", "kaynak", "neden", "satir", "surum"]


def record(day: date, source: str, reason: str, rows: int, now: datetime | None = None) -> None:
    import core

    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        first = not LOG_FILE.exists()
        with open(LOG_FILE, "a", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh, lineterminator="\n")
            if first:
                w.writerow(HEADER)
            w.writerow([(now or datetime.now()).isoformat(timespec="seconds"), day.isoformat(), source, reason,
                        int(rows), core.__version__])
    except Exception as exc:  # noqa: BLE001 - the record must never stop a training
        logger.warning("Model training not recorded | %s", exc)


__all__ = ["HEADER", "LOG_FILE", "record"]
