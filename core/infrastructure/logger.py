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

    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            LOG_FILE,
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
