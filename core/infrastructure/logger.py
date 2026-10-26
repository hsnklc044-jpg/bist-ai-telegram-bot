"""
QuantBIST
Logging Infrastructure
"""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler

from core.config.paths import LOG_DIR

LOG_FILE = LOG_DIR / "quantbist.log"
# Empty turns the log file off (the tests set it, so their deliberate
# failures never appear in the real logs/quantbist.log).
LOG_FILE_ENV = "QUANTBIST_LOG_FILE"
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

_configured = False


def _configure() -> None:
    global _configured

    if _configured:
        return

    level = os.getenv("LOG_LEVEL", "INFO").upper()

    root = logging.getLogger()
    root.setLevel(level)

    formatter = logging.Formatter(LOG_FORMAT)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    log_file = os.getenv(LOG_FILE_ENV, str(LOG_FILE))

    if log_file:
        try:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=5_000_000,
                backupCount=5,
                encoding="utf-8",
            )
            file_handler.setFormatter(formatter)
            root.addHandler(file_handler)
        except OSError:
            root.warning("Log file unavailable, logging to console only.")

    # yfinance and urllib3 are very chatty at INFO level.
    for noisy in ("yfinance", "urllib3", "httpx", "peewee"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger."""

    _configure()

    return logging.getLogger(name)
