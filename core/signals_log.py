"""
QuantBIST
Signal log: every technical view the bot shows is recorded, so that
months later "what did the bot say that day, and on which data?" has an
answer and the views can be measured.

    data/signal_log.csv
    logged_at,source,symbol,score,view,data_date,price,details
"""

from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path

from core.config.paths import SIGNAL_LOG_FILE
from core.infrastructure.logger import get_logger
from core.market.calendar import now_istanbul

logger = get_logger(__name__)

FIELDS = ("logged_at", "source", "symbol", "score", "view", "data_date", "price", "details")


def log_signal(
    source: str,
    symbol: str,
    score: float | None,
    view: str,
    data_date: date | None,
    price: float | None = None,
    details: str = "",
    path: Path | str | None = None,
    now: datetime | None = None,
) -> None:
    """Append one row. Logging must never break the bot, so errors are only logged."""

    path = Path(path or SIGNAL_LOG_FILE)
    try:
        new_file = not path.exists()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh, lineterminator="\n")
            if new_file:
                writer.writerow(FIELDS)
            writer.writerow(
                [
                    (now or now_istanbul()).isoformat(timespec="seconds"),
                    source,
                    symbol,
                    "" if score is None else f"{score:g}",
                    view,
                    data_date.isoformat() if data_date else "",
                    "" if price is None else f"{price:.10g}",
                    details,
                ]
            )
    except OSError as exc:
        logger.warning("Signal log write failed | %s", exc)


def log_analysis(source: str, result: dict, view: str, path: Path | str | None = None) -> None:
    """Log an analyzer result (as shown by /analyze, /top, /watchscan)."""

    data_date = None
    try:
        from core.market.data import load_price_history

        df = load_price_history(result["symbol"])
        if df is not None and not df.empty:
            data_date = df.index[-1].date()
    except Exception as exc:  # noqa: BLE001 - logging must not fail the command
        logger.warning("Signal log: data date unknown | %s", exc)

    parts = []
    for key in ("trend", "rsi", "macd", "volume_ratio"):
        if result.get(key) is not None:
            value = result[key]
            parts.append(f"{key}={value:.2f}" if isinstance(value, float) else f"{key}={value}")
    log_signal(
        source,
        result.get("symbol", ""),
        result.get("score"),
        view,
        data_date,
        result.get("price"),
        "; ".join(parts),
        path,
    )


__all__ = ["log_signal", "log_analysis"]
