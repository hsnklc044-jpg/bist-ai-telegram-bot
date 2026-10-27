"""
QuantBIST
Local price store (SQLite).

One row per symbol per trading day. The store keeps HISTORY_YEARS of
daily candles and only downloads what is missing, so after the first
run an update takes seconds and the bot keeps working (with the last
stored data) when the provider is unreachable.

Prices are dividend/split adjusted by the provider. Adjustment changes
old prices, so every update re-downloads an overlap window and, if the
overlap no longer matches, replaces that symbol's whole history.
"""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from core.config.paths import MARKET_DB
from core.infrastructure.logger import get_logger
from core.market.calendar import ISTANBUL
from core.market.provider import COLUMNS, get_provider

logger = get_logger(__name__)

HISTORY_YEARS = 5
OVERLAP_DAYS = 10
ADJUSTMENT_TOLERANCE = 0.005
REFRESH_MINUTES = 15

_SCHEMA = """
CREATE TABLE IF NOT EXISTS prices (
    symbol TEXT NOT NULL,
    date   TEXT NOT NULL,
    open   REAL NOT NULL,
    high   REAL NOT NULL,
    low    REAL NOT NULL,
    close  REAL NOT NULL,
    volume REAL NOT NULL,
    PRIMARY KEY (symbol, date)
);
CREATE TABLE IF NOT EXISTS sync (
    symbol     TEXT PRIMARY KEY,
    checked_at TEXT NOT NULL,
    source     TEXT NOT NULL
);
"""

_db_path: Path = MARKET_DB
_lock = threading.Lock()


def configure(path: Path) -> None:
    """Point the store at another database file (tests)."""

    global _db_path
    _db_path = Path(path)


@contextmanager
def _connect():
    _db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_db_path, timeout=30)
    try:
        conn.executescript(_SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def read(
    symbol: str,
    start: date | None = None,
) -> pd.DataFrame:
    """Stored candles for a symbol, oldest first."""

    query = "SELECT date, open, high, low, close, volume FROM prices WHERE symbol = ?"
    params: list = [symbol]

    if start is not None:
        query += " AND date >= ?"
        params.append(start.isoformat())

    query += " ORDER BY date"

    with _connect() as conn:
        df = pd.read_sql_query(query, conn, params=params)

    if df.empty:
        return pd.DataFrame(columns=list(COLUMNS))

    df["date"] = pd.to_datetime(df["date"])

    return df.set_index("date")


def last_date(symbol: str) -> date | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT MAX(date) FROM prices WHERE symbol = ?", (symbol,)
        ).fetchone()

    return date.fromisoformat(row[0]) if row and row[0] else None


def symbols() -> list[str]:
    with _connect() as conn:
        rows = conn.execute("SELECT DISTINCT symbol FROM prices ORDER BY symbol").fetchall()

    return [r[0] for r in rows]


def _write(
    conn: sqlite3.Connection,
    symbol: str,
    df: pd.DataFrame,
    replace_all: bool = False,
) -> int:
    if replace_all:
        conn.execute("DELETE FROM prices WHERE symbol = ?", (symbol,))

    rows = [
        (
            symbol,
            idx.date().isoformat(),
            float(r.open),
            float(r.high),
            float(r.low),
            float(r.close),
            float(r.volume),
        )
        for idx, r in df.iterrows()
    ]

    conn.executemany(
        "INSERT OR REPLACE INTO prices VALUES (?, ?, ?, ?, ?, ?, ?)",
        rows,
    )

    return len(rows)


def _istanbul(moment: datetime) -> datetime:
    """Istanbul time; a time without a zone is the computer's local time (PC, server or CI)."""

    return moment.astimezone(ISTANBUL)


def _checked_recently(symbol: str, now: datetime) -> bool:
    with _connect() as conn:
        row = conn.execute(
            "SELECT checked_at FROM sync WHERE symbol = ?", (symbol,)
        ).fetchone()

    if not row:
        return False

    checked = _istanbul(datetime.fromisoformat(row[0]))

    return _istanbul(now) - checked < timedelta(minutes=REFRESH_MINUTES)


def _overlap_matches(stored: pd.DataFrame, fresh: pd.DataFrame) -> bool:
    common = stored.index.intersection(fresh.index)

    if len(common) == 0:
        return True

    old = stored.loc[common, "close"]
    new = fresh.loc[common, "close"]
    drift = ((new - old).abs() / old).max()

    return bool(drift <= ADJUSTMENT_TOLERANCE)


def update(
    symbol_list: list[str],
    force: bool = False,
    now: datetime | None = None,
) -> dict[str, str]:
    """
    Bring the given symbols up to date.

    Returns {symbol: status}; status is one of
    "fresh" (checked recently, nothing done), "full", "incremental",
    "readjusted" (overlap mismatch, history replaced), "empty",
    "failed" (provider error; stored data, if any, is kept).
    """

    now = _istanbul(now or datetime.now())
    provider = get_provider()
    status: dict[str, str] = {}

    full: list[str] = []
    incremental: dict[str, date] = {}

    for symbol in symbol_list:
        if not force and _checked_recently(symbol, now):
            status[symbol] = "fresh"
            continue

        last = last_date(symbol)

        if last is None or force:
            full.append(symbol)
        else:
            incremental[symbol] = last - timedelta(days=OVERLAP_DAYS)

    history_start = (now - timedelta(days=365 * HISTORY_YEARS + 5)).date()

    batches: list[tuple[list[str], date, str]] = []
    if full:
        batches.append((full, history_start, "full"))
    if incremental:
        batches.append((list(incremental), min(incremental.values()), "incremental"))

    readjust: list[str] = []

    with _lock:
        for batch, start, mode in batches:
            try:
                fetched = provider.fetch(batch, start)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Price download failed | %s | %s", batch, exc)
                fetched = {}
                for symbol in batch:
                    status[symbol] = "failed"
                continue

            with _connect() as conn:
                for symbol in batch:
                    df = fetched.get(symbol)

                    if df is None or df.empty:
                        status.setdefault(symbol, "empty" if mode == "full" else "failed")
                        continue

                    if mode == "incremental":
                        stored = read(symbol, start=incremental[symbol])

                        if not _overlap_matches(stored, df):
                            readjust.append(symbol)
                            continue

                    _write(conn, symbol, df, replace_all=(mode == "full"))
                    status[symbol] = mode

                    conn.execute(
                        "INSERT OR REPLACE INTO sync VALUES (?, ?, ?)",
                        (symbol, now.isoformat(timespec="seconds"), provider.name),
                    )

        if readjust:
            logger.info("Adjusted history changed, re-downloading | %s", readjust)

            try:
                fetched = provider.fetch(readjust, history_start)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Re-download failed | %s | %s", readjust, exc)
                fetched = {}

            with _connect() as conn:
                for symbol in readjust:
                    df = fetched.get(symbol)

                    if df is None or df.empty:
                        status[symbol] = "failed"
                        continue

                    _write(conn, symbol, df, replace_all=True)
                    status[symbol] = "readjusted"
                    conn.execute(
                        "INSERT OR REPLACE INTO sync VALUES (?, ?, ?)",
                        (symbol, now.isoformat(timespec="seconds"), provider.name),
                    )

    changed = {k: v for k, v in status.items() if v != "fresh"}
    if changed:
        logger.info("Price store updated | %s", changed)

    return status


__all__ = [
    "HISTORY_YEARS",
    "REFRESH_MINUTES",
    "configure",
    "read",
    "last_date",
    "symbols",
    "update",
]
