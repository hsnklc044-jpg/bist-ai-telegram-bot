"""
QuantBIST
Alert log: data/alerts_log.csv keeps every state change so an alert is
sent once when it opens, again only if it gets more severe, and is
closed when its condition is gone.

    logged_at,data_date,account,symbol,rule,event,severity,value,threshold,message
    event: open | escalate | close
"""

from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path

from core.alerts.rules import Alert
from core.config.paths import ALERTS_LOG_FILE
from core.infrastructure.csvfiles import open_append, read_rows
from core.market.calendar import now_istanbul

FIELDS = ("logged_at", "data_date", "account", "symbol", "rule", "event", "severity", "value", "threshold", "message")


def _read(path: Path) -> list[dict]:
    """Rows of the alert log; a damaged file raises PersonalFileError and is not rewritten."""

    return [row for _, row in read_rows(path, ("account", "symbol", "rule", "event"))]


def open_alerts(path: Path | str | None = None) -> dict[tuple[str, str, str], dict]:
    """The last state of every alert that is currently open."""

    state: dict[tuple[str, str, str], dict] = {}
    for row in _read(Path(path or ALERTS_LOG_FILE)):
        key = (row["account"], row["symbol"], row["rule"])
        if row["event"] == "close":
            state.pop(key, None)
        else:
            state[key] = row
    return state


def update_alert_log(
    alerts: list[Alert],
    data_date: date,
    path: Path | str | None = None,
    now: datetime | None = None,
    write: bool = True,
) -> list[tuple[str, Alert | dict]]:
    """
    Compare today's alerts with the open ones and append the changes.
    Returns the events [(event, alert_or_row)] that should be reported.
    write=False only reports them (/report by hand: the 18:30 report still shows them as new).
    """

    path = Path(path or ALERTS_LOG_FILE)
    current = open_alerts(path)
    now = (now or now_istanbul()).isoformat(timespec="seconds")
    events: list[tuple[str, Alert | dict]] = []
    rows: list[list] = []

    seen = set()
    for a in alerts:
        seen.add(a.key)
        before = current.get(a.key)
        if before is None:
            event = "open"
        elif a.severity > int(before["severity"]):
            event = "escalate"
        else:
            continue
        events.append((event, a))
        rows.append([now, a.data_date.isoformat(), a.account, a.symbol, a.rule, event, a.severity,
                     f"{a.value:.6g}", f"{a.threshold:.6g}", a.message])

    for key, row in current.items():
        if key not in seen:
            events.append(("close", row))
            rows.append([now, data_date.isoformat(), *key, "close", row["severity"], "", "", "koşul ortadan kalktı"])

    if rows and write:
        fh, new_file = open_append(path)
        with fh:
            writer = csv.writer(fh, lineterminator="\n")
            if new_file:
                writer.writerow(FIELDS)
            writer.writerows(rows)
    return events


__all__ = ["open_alerts", "update_alert_log"]
