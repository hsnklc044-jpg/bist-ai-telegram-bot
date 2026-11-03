"""
QuantBIST
Paper signal book (BIST 30 hedefi, adım 3, K-60): every signal the ML screen produces is written to
SQLite (data/signals.db) and followed with the prices: enter at the next session's open, 2% stop,
4% target, at most HORIZON sessions; the same rules as the ML labels (core.ml.features), so what
is followed is what was measured. Each signal is a fixed SIZE of a virtual CAPITAL.

The circuit breaker (şalter): when the book's value falls BREAKER (6%) or more in one session,
no new signal is accepted for the next session. Virtual only: no order, no broker. Rule output,
not advice.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from core.config.paths import SIGNALS_DB
from core.ml.features import COST, HORIZON, LIMIT_MOVE, STOP, TARGET

CAPITAL = 100_000.0
SIZE = 10_000.0
BREAKER = 0.06
OPEN_STATES = ("bekliyor", "acik")
DISCLAIMER = "Sanal kayıttır; emir oluşturulmaz. Kural çıktısıdır, öneri değildir."

SCHEMA = """
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created TEXT NOT NULL,            -- signal day (its close); entry is the next session's open
    symbol TEXT NOT NULL,
    signal_close REAL NOT NULL,
    proba REAL,
    source TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'bekliyor',   -- bekliyor, acik, hedef, stop, sure, dolmadi
    entry_date TEXT, entry_price REAL, stop REAL, target REAL,
    exit_date TEXT, exit_price REAL, r REAL,
    UNIQUE (created, symbol)
);
CREATE TABLE IF NOT EXISTS breaker (
    day TEXT PRIMARY KEY,             -- the session whose fall tripped it; blocks the next one
    change REAL NOT NULL
);
"""


class BreakerTripped(Exception):
    pass


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    path = Path(path or SIGNALS_DB)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


@dataclass
class Signal:
    id: int
    created: date
    symbol: str
    status: str
    entry_date: date | None
    entry_price: float | None
    stop: float | None
    target: float | None
    exit_date: date | None
    exit_price: float | None
    r: float | None
    proba: float | None

    @classmethod
    def of(cls, row: sqlite3.Row) -> Signal:
        def d(x):
            return date.fromisoformat(x) if x else None

        return cls(row["id"], d(row["created"]), row["symbol"], row["status"], d(row["entry_date"]),
                   row["entry_price"], row["stop"], row["target"], d(row["exit_date"]), row["exit_price"], row["r"],
                   row["proba"])


def signals(conn: sqlite3.Connection, states=None) -> list[Signal]:
    rows = conn.execute("SELECT * FROM signals ORDER BY created, symbol").fetchall()
    return [Signal.of(r) for r in rows if states is None or r["status"] in states]


def blocked(conn: sqlite3.Connection, day: date) -> bool:
    """The breaker tripped on session `day`: the signals of that close (they would enter the next
    session) are refused. The daily run checks the breaker before it adds the day's signals."""

    return conn.execute("SELECT 1 FROM breaker WHERE day = ?", (day.isoformat(),)).fetchone() is not None


def add(conn: sqlite3.Connection, day: date, symbol: str, close: float, proba: float | None = None,
        source: str = "tara-ml") -> int | None:
    """Record a signal of `day`; None when one exists for the stock that day. Refused while the
    breaker holds."""

    if blocked(conn, day):
        raise BreakerTripped(f"şalter açık: {day:%d.%m.%Y} için yeni sinyal alınmadı")
    with conn:
        cur = conn.execute("INSERT OR IGNORE INTO signals (created, symbol, signal_close, proba, source) "
                           "VALUES (?, ?, ?, ?, ?)", (day.isoformat(), symbol, close, proba, source))
    return cur.lastrowid if cur.rowcount else None


def _follow(s: Signal, df: pd.DataFrame) -> dict:
    """The signal's state on the candles of `df` (final candles only)."""

    after = df[df.index > pd.Timestamp(s.created)]
    if after.empty:
        return {}
    first = after.iloc[0]
    prev_close = float(df.loc[df.index <= pd.Timestamp(s.created), "close"].iloc[-1])
    entry = float(first["open"])
    if not entry > 0 or entry / prev_close - 1 >= LIMIT_MOVE:
        return {"status": "dolmadi", "entry_date": after.index[0].date().isoformat(), "r": None}
    stop, target = entry * (1 - STOP), entry * (1 + TARGET)
    out = {"status": "acik", "entry_date": after.index[0].date().isoformat(), "entry_price": entry, "stop": stop,
           "target": target}
    window = after.iloc[:HORIZON]
    for day, c in window.iterrows():
        if c["low"] <= stop:
            price = min(stop, float(c["open"]))
            return out | {"status": "stop", "exit_date": day.date().isoformat(), "exit_price": price,
                          "r": price / entry - 1 - COST}
        if c["high"] >= target:
            price = max(target, float(c["open"]))
            return out | {"status": "hedef", "exit_date": day.date().isoformat(), "exit_price": price,
                          "r": price / entry - 1 - COST}
    if len(window) == HORIZON:
        last = window.index[-1]
        price = float(window["close"].iloc[-1])
        return out | {"status": "sure", "exit_date": last.date().isoformat(), "exit_price": price,
                      "r": price / entry - 1 - COST}
    return out


def update(conn: sqlite3.Connection, bars) -> int:
    """Follow every waiting / open signal with `bars(symbol) -> final daily candles`; returns how many changed."""

    changed = 0
    for s in signals(conn, OPEN_STATES):
        df = bars(s.symbol)
        if df is None or df.empty:
            continue
        state = _follow(s, df)
        if not state or (state["status"] == s.status and state.get("exit_date") is None and s.entry_price):
            continue
        cols = ", ".join(f"{k} = ?" for k in state)
        with conn:
            conn.execute(f"UPDATE signals SET {cols} WHERE id = ?", (*state.values(), s.id))
        changed += 1
    return changed


def equity(conn: sqlite3.Connection, bars, days) -> pd.Series:
    """The book's value at each day's close: CAPITAL + closed results + open positions at that close."""

    every = signals(conn)
    closes = {}
    out = {}
    for day in days:
        day = pd.Timestamp(day)
        value = CAPITAL
        for s in every:
            if s.entry_price is None or s.entry_date is None or pd.Timestamp(s.entry_date) > day:
                continue
            if s.exit_date is not None and pd.Timestamp(s.exit_date) <= day:
                value += SIZE * (s.r or 0.0)
                continue
            if s.symbol not in closes:
                df = bars(s.symbol)
                closes[s.symbol] = df["close"] if df is not None and not df.empty else pd.Series(dtype=float)
            seen = closes[s.symbol][closes[s.symbol].index <= day]
            if not seen.empty:
                value += SIZE * (float(seen.iloc[-1]) / s.entry_price - 1)
        out[day] = value
    return pd.Series(out, dtype=float)


def check_breaker(conn: sqlite3.Connection, bars, day: date, previous: date) -> float | None:
    """The session's change of the book's value; trips the breaker at BREAKER or worse."""

    values = equity(conn, bars, [previous, day])
    change = values.iloc[1] / values.iloc[0] - 1
    if change <= -BREAKER + 1e-12:
        with conn:
            conn.execute("INSERT OR REPLACE INTO breaker (day, change) VALUES (?, ?)", (day.isoformat(), change))
    return float(change)


def summary(conn: sqlite3.Connection, bars, day: date) -> str:
    """The /durum lines: book value, open and closed signals, hit rate, breaker."""

    every = signals(conn)
    closed = [s for s in every if s.status in ("hedef", "stop", "sure")]
    open_ = [s for s in every if s.status in OPEN_STATES]
    value = equity(conn, bars, [day]).iloc[0]
    hits = sum(s.status == "hedef" for s in closed)

    def pct(x):
        return f"%{x * 100:+.1f}".replace(".", ",")

    lines = [f"🧪 Sanal sinyal defteri: {value:,.0f} TL ({pct(value / CAPITAL - 1)}); açık {len(open_)}, "
             f"kapanan {len(closed)}" + (f", hedefe ulaşan %{hits / len(closed) * 100:.0f}" if closed else "")]
    if blocked(conn, day):
        lines.append(f"⛔ Şalter açık: bugün defter %{BREAKER * 100:.0f} veya daha fazla düştü; bugünün sinyalleri "
                     "kaydedilmedi.")
    return "\n".join(lines)


__all__ = ["BREAKER", "BreakerTripped", "CAPITAL", "DISCLAIMER", "SIZE", "Signal", "add", "blocked", "check_breaker",
           "connect", "equity", "signals", "summary", "update"]
