"""
QuantBIST
Paper signal book (BIST 30 hedefi, adım 3, K-60): every signal the ML screen produces is written to
SQLite (data/signals.db) and followed with the prices: enter at the next session's open, 2% stop,
4% target, at most HORIZON sessions; the same rules as the ML labels (core.ml.features), so what
is followed is what was measured. Each signal is a fixed SIZE of a virtual CAPITAL.

Followed twice: during the session every hour on hourly candles (core.signals.live, stop and
target only), and after the close on the final daily candles (also the 10-session expiry).

The circuit breaker (şalter, K-65): when the signals closed during one day lose BREAKER (6%) of
the book's realized value at the start of that day, the bot locks itself for the rest of the
day: /tara and new signals are refused. Virtual only: no order, no broker. Rule output, not advice.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from core.config.paths import SIGNALS_DB
from core.infrastructure.logger import get_logger
from core.ml.features import COST, HORIZON, LIMIT_MOVE, STOP, TARGET

logger = get_logger(__name__)

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
    """The breaker tripped on `day` (K-65): no scan and no new signal for the rest of that day."""

    return conn.execute("SELECT 1 FROM breaker WHERE day = ?", (day.isoformat(),)).fetchone() is not None


def add(conn: sqlite3.Connection, day: date, symbol: str, close: float, proba: float | None = None,
        source: str = "tara-ml") -> int | None:
    """Record a signal of `day`; None when one exists for the stock that day. Refused while the
    breaker holds."""

    from core.signals import panic

    if panic.active():
        raise BreakerTripped("panik kilidi açık (/devam ile kalkar): yeni sinyal alınmadı")
    if blocked(conn, day):
        raise BreakerTripped(f"şalter açık: {day:%d.%m.%Y} için yeni sinyal alınmadı")
    with conn:
        cur = conn.execute("INSERT OR IGNORE INTO signals (created, symbol, signal_close, proba, source) "
                           "VALUES (?, ?, ?, ?, ?)", (day.isoformat(), symbol, close, proba, source))
    return cur.lastrowid if cur.rowcount else None


def _days(index: pd.Index) -> pd.DatetimeIndex:
    """Session dates of daily (naive) or hourly (Istanbul time) candles."""

    index = pd.DatetimeIndex(index)
    if index.tz is not None:
        index = index.tz_convert("Europe/Istanbul").tz_localize(None)
    return index.normalize()


def _follow(s: Signal, df: pd.DataFrame, expire: bool = True) -> dict:
    """The signal's state on the final candles of `df`, daily or hourly: the first candle after the
    signal day is the entry (its open); stop and target are checked candle by candle (both in one
    candle: stop); `expire` closes it at the HORIZON-th session's last close (daily candles only:
    an hourly frame cannot tell that the session is over)."""

    days = _days(df.index)
    signal_day = pd.Timestamp(s.created)
    after, after_days = df[days > signal_day], days[days > signal_day]
    before = df[days <= signal_day]
    if after.empty:
        return {}
    entry = float(after["open"].iloc[0])
    entry_day = after_days[0].date().isoformat()
    if not entry > 0 or (not before.empty and entry / float(before["close"].iloc[-1]) - 1 >= LIMIT_MOVE):
        return {"status": "dolmadi", "entry_date": entry_day, "r": None}
    stop, target = entry * (1 - STOP), entry * (1 + TARGET)
    out = {"status": "acik", "entry_date": entry_day, "entry_price": entry, "stop": stop, "target": target}
    sessions = after_days.unique()
    window = after[after_days <= sessions[min(HORIZON, len(sessions)) - 1]]
    window_days = _days(window.index)
    lows, highs, opens = (window[k].to_numpy(dtype=float) for k in ("low", "high", "open"))
    hit = np.flatnonzero((lows <= stop) | (highs >= target))
    if len(hit):
        i = hit[0]
        if lows[i] <= stop:  # both in one candle counts as the stop
            status, price = "stop", min(stop, opens[i])
        else:
            status, price = "hedef", max(target, opens[i])
        return out | {"status": status, "exit_date": window_days[i].date().isoformat(), "exit_price": price,
                      "r": price / entry - 1 - COST}
    if expire and len(sessions) >= HORIZON:
        price = float(window["close"].iloc[-1])
        return out | {"status": "sure", "exit_date": window_days[-1].date().isoformat(), "exit_price": price,
                      "r": price / entry - 1 - COST}
    return out


def update(conn: sqlite3.Connection, bars, expire: bool = True) -> list[Signal]:
    """Follow every waiting / open signal with `bars(symbol)` (final daily candles; or hourly ones
    with expire=False, core.signals.live); returns the signals whose state changed, as now stored."""

    changed = []
    for s in signals(conn, OPEN_STATES):
        try:
            df = bars(s.symbol)
            if df is None or df.empty:
                continue
            state = _follow(s, df, expire)
        except Exception as exc:  # noqa: BLE001 - one stock's bad data must not stop the others
            logger.warning("Signal follow failed | %s | %s", s.symbol, exc)
            continue
        if not state or (state["status"] == s.status and state.get("exit_date") is None and s.entry_price):
            continue
        cols = ", ".join(f"{k} = ?" for k in state)
        with conn:
            conn.execute(f"UPDATE signals SET {cols} WHERE id = ?", (*state.values(), s.id))
        changed.append(next(x for x in signals(conn) if x.id == s.id))
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


def realized(conn: sqlite3.Connection, day: date) -> float:
    """K-65: the net result of the signals closed on `day`, as a share of the book's realized value
    at the start of that day (CAPITAL + everything closed before it)."""

    closed = [s for s in signals(conn) if s.exit_date is not None and s.r is not None]
    start = CAPITAL + SIZE * sum(s.r for s in closed if s.exit_date < day)
    today_tl = SIZE * sum(s.r for s in closed if s.exit_date == day)
    return today_tl / start if start > 0 else 0.0


def check_breaker(conn: sqlite3.Connection, day: date) -> float:
    """Trips the breaker when the day's closed losses reach BREAKER (6%) of the book (K-65)."""

    change = realized(conn, day)
    if change <= -BREAKER + 1e-12 and not blocked(conn, day):
        with conn:
            conn.execute("INSERT OR REPLACE INTO breaker (day, change) VALUES (?, ?)", (day.isoformat(), change))
        logger.warning("Circuit breaker tripped | %s | %.4f", day, change)
    return change


def locked(day: date, path: Path | str | None = None) -> bool:
    """For /tara and the scans: is the breaker on today, or the panic lock? Never creates the book file."""

    from core.signals import panic

    if panic.active():
        return True
    path = Path(path or SIGNALS_DB)
    if not path.exists():
        return False
    try:
        conn = connect(path)
        try:
            return blocked(conn, day)
        finally:
            conn.close()
    except sqlite3.Error as exc:
        logger.warning("Breaker check failed | %s", exc)
        return False


def _last_price(bars, symbol: str) -> float | None:
    try:
        df = bars(symbol)
        return float(df["close"].iloc[-1]) if df is not None and not df.empty else None
    except Exception as exc:  # noqa: BLE001 - /durum must still answer
        logger.warning("Last price failed | %s | %s", symbol, exc)
        return None


def summary(conn: sqlite3.Connection, bars, day: date) -> str:
    """The /durum lines: the virtual cash box (realized and with the open signals at their last
    price), each open signal's live profit or loss, the hit rate and the breaker."""

    every = signals(conn)
    closed = [s for s in every if s.status in ("hedef", "stop", "sure")]
    open_ = [s for s in every if s.status in OPEN_STATES]
    hits = sum(s.status == "hedef" for s in closed)
    realized_value = CAPITAL + SIZE * sum(s.r for s in closed if s.r is not None)

    def pct(x):
        return f"%{x * 100:+.2f}".replace(".", ",")

    def tl(x):
        return f"{x:,.0f}".replace(",", ".") + " TL"

    def px(x):
        return f"{x:.2f}".replace(".", ",")

    rows, open_pnl = [], 0.0
    for s in open_:
        code = s.symbol.removesuffix(".IS")
        if s.status == "bekliyor" or not s.entry_price:
            rows.append(f"  {code}: giriş bekliyor (sinyal {s.created:%d.%m})")
            continue
        price = _last_price(bars, s.symbol)
        if price is None:
            rows.append(f"  {code}: giriş {px(s.entry_price)}, son fiyat yok")
            continue
        r = price / s.entry_price - 1
        open_pnl += SIZE * r
        rows.append(f"  {code}: giriş {px(s.entry_price)} → son {px(price)} ({pct(r)}, {tl(SIZE * r)}); "
                    f"stop {px(s.stop)}, hedef {px(s.target)}")
    value = realized_value + open_pnl
    lines = [f"🧪 Sanal kasa: {tl(value)} ({pct(value / CAPITAL - 1)}); gerçekleşmiş {tl(realized_value)}, "
             f"açık pozisyonlar {tl(open_pnl)}",
             f"Açık sinyal {len(open_)}, kapanan {len(closed)}"
             + (f", hedefe ulaşan %{hits / len(closed) * 100:.0f}" if closed else ""), *rows]
    from core.signals import panic

    if panic.active():
        lines.append(f"⛔ Panik kilidi açık ({panic.since()}): takip ve taramalar durdu. Kaldırmak için /devam.")
    if blocked(conn, day):
        lines.append(f"⛔ Şalter açık: bugün kapanan işlemlerin zararı %{BREAKER * 100:.0f} sınırına ulaştı; "
                     "bugün tarama ve yeni sinyal yok.")
    return "\n".join(lines)


__all__ = ["BREAKER", "BreakerTripped", "CAPITAL", "DISCLAIMER", "SIZE", "Signal", "add", "blocked", "check_breaker",
           "connect", "equity", "locked", "realized", "signals", "summary", "update"]
