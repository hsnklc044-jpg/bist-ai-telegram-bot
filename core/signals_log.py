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
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

from core.config.paths import SIGNAL_LOG_FILE
from core.infrastructure.logger import get_logger
from core.market.calendar import (
    is_session_day,
    last_final_session_date,
    now_istanbul,
    sessions_between,
)

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


@dataclass
class LogAudit:
    """Integrity of the daily (systematic) records in signal_log.csv."""

    rows: int = 0
    bad_rows: int = 0  # unreadable date, timestamp or symbol
    duplicates: int = 0  # same symbol and data date twice
    days: list[date] = field(default_factory=list)
    missing: list[date] = field(default_factory=list)  # sessions without any record
    late: list[date] = field(default_factory=list)  # recorded after a newer close was available

    @property
    def problems(self) -> bool:
        return bool(self.bad_rows or self.duplicates or self.missing or self.late)

    def text(self) -> str:
        if not self.days:
            return "günlük kayıt yok"
        parts = [f"{len(self.days)} gün, {self.rows} kayıt; {self.days[0]:%d.%m.%Y} – {self.days[-1]:%d.%m.%Y}"]
        if self.missing:
            shown = ", ".join(f"{d:%d.%m}" for d in self.missing[-5:])
            parts.append(f"kaydı olmayan {len(self.missing)} seans ({shown})")
        if self.late:
            parts.append(f"{len(self.late)} gün eski veriyle kaydedilmiş")
        if self.duplicates:
            parts.append(f"{self.duplicates} tekrar kayıt")
        if self.bad_rows:
            parts.append(f"{self.bad_rows} okunamayan satır")
        return "; ".join(parts)


def audit_log(
    path: Path | str | None = None,
    now: datetime | None = None,
    source: str = "daily",
) -> LogAudit:
    """
    Check the daily records: duplicates, unreadable rows, sessions with no
    record (computer off, report failed) and records written with stale
    data (the newest close was already final but not in the store).
    Missing sessions are counted from the first record up to the latest
    final session; they shrink the sample, the results are not corrected.
    """

    path = Path(path or SIGNAL_LOG_FILE)
    result = LogAudit()
    if not path.exists():
        return result

    with open(path, encoding="utf-8", newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if r.get("source") == source]

    seen: set[tuple[str, date]] = set()
    days: set[date] = set()
    late: set[date] = set()
    for r in rows:
        try:
            day = date.fromisoformat(r["data_date"])
            logged = datetime.fromisoformat(r["logged_at"])
            symbol = r["symbol"].strip()
            if not symbol:
                raise ValueError("symbol")
        except (KeyError, TypeError, ValueError):
            result.bad_rows += 1
            continue
        result.rows += 1
        if (symbol, day) in seen:
            result.duplicates += 1
        seen.add((symbol, day))
        days.add(day)
        if sessions_between(day, last_final_session_date(logged)) > 0:
            late.add(day)

    result.days = sorted(days)
    result.late = sorted(late)
    if result.days:
        expected = last_final_session_date(now)
        day, missing = result.days[0], []
        while day < expected:
            day += timedelta(days=1)
            if is_session_day(day) and day not in days:
                missing.append(day)
        result.missing = missing

    return result


__all__ = ["LogAudit", "audit_log", "log_signal", "log_analysis"]
