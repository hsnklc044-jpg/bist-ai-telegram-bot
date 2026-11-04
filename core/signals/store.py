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

import math
import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from core.config.paths import SIGNALS_DB
from core.infrastructure.logger import get_logger
from core.market.limits import limit_up, locked_down
from core.ml.features import COST, HORIZON, STOP, TARGET

logger = get_logger(__name__)

CAPITAL = 100_000.0
SIZE = 10_000.0
BREAKER = 0.06
RISK = 0.01  # K-67: a stop may cost at most 1% of the cash box
OPEN_STATES = ("bekliyor", "acik")
PENDING = "onay_bekliyor"
DISCLAIMER = "Sanal kayıttır; emir oluşturulmaz. Kural çıktısıdır, öneri değildir."

SCHEMA = """
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created TEXT NOT NULL,            -- signal day (its close); entry is the next session's open
    symbol TEXT NOT NULL,
    signal_close REAL NOT NULL,
    proba REAL,
    source TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'bekliyor',   -- onay_bekliyor, bekliyor, acik, hedef, stop, sure, dolmadi,
                                               -- reddedildi, zaman_asimi, iptal
    entry_date TEXT, entry_price REAL, stop REAL, target REAL,
    exit_date TEXT, exit_price REAL, r REAL,
    qty INTEGER,                      -- K-67: lots (NULL: the fixed SIZE of K-60)
    peak REAL,                        -- K-67: highest price since the entry (the trailing stop's anchor)
    reason TEXT,                      -- K-70: why (trigger, indicators, model probability)
    risk_tl REAL,                     -- K-70: the loss if the stop hits at the signal price (lots × close × STOP)
    valid_until TEXT,                 -- K-70: the last day the signal can be entered (a card: its own day)
    horizon INTEGER,                  -- K-70: then at most this many sessions in the trade
    bench_r REAL,                     -- K-70: BIST 100 over the same days (entry open → exit close)
    UNIQUE (created, symbol)
);
CREATE TABLE IF NOT EXISTS breaker (
    day TEXT PRIMARY KEY,             -- the session whose closed losses tripped it; blocks that same day
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
    have = {r["name"] for r in conn.execute("PRAGMA table_info(signals)")}
    for column, kind in (("qty", "INTEGER"), ("peak", "REAL"), ("reason", "TEXT"), ("risk_tl", "REAL"),
                         ("valid_until", "TEXT"), ("horizon", "INTEGER"), ("bench_r", "REAL")):  # older books
        if column not in have:
            conn.execute(f"ALTER TABLE signals ADD COLUMN {column} {kind}")
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
    qty: int | None = None
    peak: float | None = None
    signal_close: float | None = None

    @classmethod
    def of(cls, row: sqlite3.Row) -> Signal:
        def d(x):
            return date.fromisoformat(x) if x else None

        return cls(row["id"], d(row["created"]), row["symbol"], row["status"], d(row["entry_date"]),
                   row["entry_price"], row["stop"], row["target"], d(row["exit_date"]), row["exit_price"], row["r"],
                   row["proba"], row["qty"], row["peak"], row["signal_close"])

    @property
    def notional(self) -> float:
        """The money in the position: lots × entry (K-67), or the fixed SIZE (K-60)."""

        return self.qty * self.entry_price if self.qty and self.entry_price else SIZE


def signals(conn: sqlite3.Connection, states=None) -> list[Signal]:
    rows = conn.execute("SELECT * FROM signals ORDER BY created, symbol").fetchall()
    return [Signal.of(r) for r in rows if states is None or r["status"] in states]


def blocked(conn: sqlite3.Connection, day: date) -> bool:
    """The breaker tripped on `day` (K-65): no scan and no new signal for the rest of that day."""

    return conn.execute("SELECT 1 FROM breaker WHERE day = ?", (day.isoformat(),)).fetchone() is not None


def add(conn: sqlite3.Connection, day: date, symbol: str, close: float, proba: float | None = None,
        source: str = "tara-ml", qty: int | None = None, status: str = "bekliyor",
        reason: str | None = None) -> int | None:
    """Record a signal of `day`; None when one exists for the stock that day. Refused while the
    breaker holds."""

    from core.signals import panic

    if panic.active():
        raise BreakerTripped("panik kilidi açık (/devam ile kalkar): yeni sinyal alınmadı")
    if blocked(conn, day):
        raise BreakerTripped(f"şalter açık: {day:%d.%m.%Y} için yeni sinyal alınmadı")
    with conn:
        cur = conn.execute(
            "INSERT OR IGNORE INTO signals (created, symbol, signal_close, proba, source, qty, status, reason, risk_tl, "
            "valid_until, horizon) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (day.isoformat(), symbol, close, proba, source, qty, status, reason,
             qty * close * STOP if qty else SIZE * STOP, day.isoformat(), HORIZON))
    return cur.lastrowid if cur.rowcount else None


def cash(conn: sqlite3.Connection) -> tuple[float, float]:
    """(realized cash box, free cash): CAPITAL + closed results; minus the open positions' cost."""

    every = signals(conn)
    box = CAPITAL + sum(s.notional * s.r for s in every if s.r is not None and s.exit_date is not None)
    used = sum(s.notional if s.entry_price else (s.qty or 0) * (s.signal_close or 0) or SIZE
               for s in every if s.status in OPEN_STATES)
    return box, box - used


def size_position(box: float, free: float, price: float, risk: float = RISK, stop: float = STOP) -> int:
    """K-67: the lots whose stop costs `risk` of the box, at most what the free cash buys."""

    if not price > 0:
        return 0
    lots = math.floor(box * risk / (price * stop))
    return max(0, min(lots, math.floor(max(free, 0.0) / price)))


def decide(conn: sqlite3.Connection, signal_id: int, enter: bool, today: date) -> str:
    """A button on a /tara ai card: enter (the next session's open) or reject. Returns the outcome."""

    from core.signals import panic

    row = conn.execute("SELECT * FROM signals WHERE id = ?", (signal_id,)).fetchone()
    if row is None:
        return "yok"
    s = Signal.of(row)
    if s.status != PENDING:
        return f"zaten:{s.status}"
    if not enter:
        new = "reddedildi"
    elif panic.active() or blocked(conn, today):
        return "kilitli"
    elif s.created != today:
        new = "zaman_asimi"  # the card's analysis is old and its entry open may have passed
    else:
        new = "bekliyor"
    if new == "bekliyor" and s.qty and s.signal_close:
        # v0.99.52 (M32-1): every card was sized on the same free cash; the button re-checks it
        _, free = cash(conn)
        lots = min(s.qty, math.floor(max(free, 0.0) / s.signal_close))
        if lots <= 0:
            return "nakit_yok"
        if lots != s.qty:
            with conn:
                conn.execute("UPDATE signals SET qty = ?, risk_tl = ? WHERE id = ?",
                             (lots, lots * s.signal_close * STOP, signal_id))
    with conn:
        conn.execute("UPDATE signals SET status = ? WHERE id = ?", (new, signal_id))
    return new


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

    # a candle with a missing or non-positive price is bad data, not a market move (M32-5, M32-6):
    # it closed positions at 0 (r = −100,15%) or ended them with a NULL result
    prices = df[["open", "high", "low", "close"]]
    df = df[(prices > 0).all(axis=1) & prices.notna().all(axis=1)]
    days = _days(df.index)
    signal_day = pd.Timestamp(s.created)
    after, after_days = df[days > signal_day], days[days > signal_day]
    before = df[days <= signal_day]
    if after.empty:
        return {}
    entry = float(after["open"].iloc[0])
    entry_day = after_days[0].date().isoformat()
    if not entry > 0 or (not before.empty and limit_up(entry / float(before["close"].iloc[-1]) - 1)):
        return {"status": "dolmadi", "entry_date": entry_day, "r": None}
    first_stop, target = entry * (1 - STOP), entry * (1 + TARGET)
    sessions = after_days.unique()
    window = after[after_days <= sessions[min(HORIZON, len(sessions)) - 1]]
    window_days = _days(window.index)
    lows, highs, opens = (window[k].to_numpy(dtype=float) for k in ("low", "high", "open"))
    # K-75: a day locked at the lower limit has no seller's fill; the stop fills at the next open
    every_locked = pd.Series(locked_down(df), index=df.index)
    locked = every_locked.reindex(window.index).fillna(False).to_numpy(dtype=bool)
    # K-67 trailing stop: STOP below the highest price seen BEFORE each candle (a candle's own high
    # cannot lift its own stop: the order inside a candle is unknown); it only moves up
    peak_before = np.maximum.accumulate(np.r_[entry, highs[:-1]])
    trail = np.maximum(first_stop, peak_before * (1 - STOP))
    peak = float(max(entry, highs.max()))
    out = {"status": "acik", "entry_date": entry_day, "entry_price": entry, "target": target, "peak": peak,
           "stop": max(first_stop, peak * (1 - STOP))}
    hit = np.flatnonzero(((lows <= trail) & ~locked) | (highs >= target))
    if len(hit):
        i = hit[0]
        if lows[i] <= trail[i]:  # both in one candle counts as the stop
            status, price = "stop", min(trail[i], opens[i])
        else:
            status, price = "hedef", max(target, opens[i])
        return out | {"status": status, "exit_date": window_days[i].date().isoformat(), "exit_price": price,
                      "r": price / entry - 1 - COST, "stop": float(trail[i]),
                      "peak": float(max(entry, highs[: i + 1].max()))}
    if expire and len(sessions) >= HORIZON:
        if locked[-1]:  # M32 re-validation O3: a locked last session has no seller; the first unlocked open
            later = df[(df.index > window.index[-1]) & ~every_locked.to_numpy(dtype=bool)]
            if later.empty:
                return out
            price = float(later["open"].iloc[0])
            return out | {"status": "sure", "exit_date": _days(later.index)[0].date().isoformat(),
                          "exit_price": price, "r": price / entry - 1 - COST}
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
        if not state or (state["status"] == s.status and state.get("exit_date") is None and s.entry_price
                         and state.get("peak") == s.peak):
            continue
        if s.entry_price is None and state.get("entry_price") and s.qty:
            state = state | {"risk_tl": s.qty * state["entry_price"] * STOP}  # M32-10: risk at the real entry
        cols = ", ".join(f"{k} = ?" for k in state)
        with conn:
            conn.execute(f"UPDATE signals SET {cols} WHERE id = ?", (*state.values(), s.id))
        changed.append(next(x for x in signals(conn) if x.id == s.id))
    return changed


BENCHMARK = "XU100.IS"


@dataclass
class Performance:
    closed: int = 0
    winners: int = 0
    losers: int = 0
    mean: float | None = None
    win_mean: float | None = None
    loss_mean: float | None = None
    bench_mean: float | None = None  # BIST 100 over the same days; None when it could not be read
    compared: int = 0  # closed signals with a benchmark result

    @property
    def excess(self) -> float | None:
        return None if self.mean is None or self.bench_mean is None else self.mean - self.bench_mean


def _bench(df: pd.DataFrame | None, entry: date, exit_: date) -> float | None:
    """BIST 100 from the entry day's open to the exit day's close (the trade's own days)."""

    if df is None or df.empty:
        return None
    days = pd.DatetimeIndex(df.index).normalize()
    start, end = df[days == pd.Timestamp(entry)], df[days == pd.Timestamp(exit_)]
    if start.empty or end.empty or not float(start["open"].iloc[0]) > 0:
        return None
    return float(end["close"].iloc[-1]) / float(start["open"].iloc[0]) - 1


def performance(conn: sqlite3.Connection, bars) -> Performance:
    """K-70: closed signals, winners and losers apart, against BIST 100 over the same days.
    A benchmark result is written on the row once known (a record, not recomputed later)."""

    done = [s for s in signals(conn) if s.r is not None and s.exit_date is not None and s.entry_date is not None]
    out = Performance(closed=len(done))
    if not done:
        return out
    wins, losses = [s.r for s in done if s.r > 0], [s.r for s in done if s.r <= 0]
    out.winners, out.losers = len(wins), len(losses)
    out.mean = sum(s.r for s in done) / len(done)
    out.win_mean = sum(wins) / len(wins) if wins else None
    out.loss_mean = sum(losses) / len(losses) if losses else None
    stored = {r["id"]: r["bench_r"] for r in conn.execute("SELECT id, bench_r FROM signals")}
    index, benches = None, []
    for s in done:
        b = stored.get(s.id)
        if b is None:
            if index is None:
                index = bars(BENCHMARK)
            b = _bench(index, s.entry_date, s.exit_date)
            if b is not None:
                with conn:
                    conn.execute("UPDATE signals SET bench_r = ? WHERE id = ?", (b, s.id))
        if b is not None:
            benches.append((s.r, b))
    if benches and len(benches) == len(done):
        out.bench_mean, out.compared = sum(b for _, b in benches) / len(benches), len(benches)
    else:
        out.compared = len(benches)
    return out


def performance_text(p: Performance) -> str:
    def pct(x):
        return f"%{x * 100:+.2f}".replace(".", ",")

    if not p.closed:
        return "📏 Sinyal performansı: kapanmış sinyal yok."
    parts = [f"📏 Sinyal performansı: {p.closed} kapanmış, ort. {pct(p.mean)}",
             f"Kazanan {p.winners}" + (f" (ort. {pct(p.win_mean)})" if p.win_mean is not None else ""),
             f"kaybeden {p.losers}" + (f" (ort. {pct(p.loss_mean)})" if p.loss_mean is not None else "")]
    if p.bench_mean is None:
        parts.append(f"BIST 100 karşılaştırması yok ({p.compared}/{p.closed} işlemde endeks verisi)")
    else:
        parts.append(f"BIST 100 aynı günlerde ort. {pct(p.bench_mean)}; fark {pct(p.excess)}")
    return "; ".join(parts) + ". Küçük örneklem: sonuç ancak çok sayıda sinyalle anlam kazanır."


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
                value += s.notional * (s.r or 0.0)
                continue
            if s.symbol not in closes:
                df = bars(s.symbol)
                closes[s.symbol] = df["close"] if df is not None and not df.empty else pd.Series(dtype=float)
            seen = closes[s.symbol][closes[s.symbol].index <= day]
            if not seen.empty:
                value += s.notional * (float(seen.iloc[-1]) / s.entry_price - 1)
        out[day] = value
    return pd.Series(out, dtype=float)


def realized(conn: sqlite3.Connection, day: date) -> float:
    """K-65: the net result of the signals closed on `day`, as a share of the book's realized value
    at the start of that day (CAPITAL + everything closed before it)."""

    closed = [s for s in signals(conn) if s.exit_date is not None and s.r is not None]
    start = CAPITAL + sum(s.notional * s.r for s in closed if s.exit_date < day)
    today_tl = sum(s.notional * s.r for s in closed if s.exit_date == day)
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


def expire_pending(conn: sqlite3.Connection, today: date) -> int:
    """Cards nobody pressed on their own day become "zaman_asimi" (v0.99.39): the analysis is old and
    the entry open has passed, exactly as a late button press. Returns how many expired."""

    with conn:
        cur = conn.execute("UPDATE signals SET status = 'zaman_asimi' WHERE status = ? AND created < ?",
                           (PENDING, today.isoformat()))
    return cur.rowcount


def summary(conn: sqlite3.Connection, bars, day: date) -> str:
    """The /durum lines: the virtual cash box (realized and with the open signals at their last
    price), each open signal's live profit or loss, the hit rate and the breaker."""

    every = signals(conn)
    closed = [s for s in every if s.status in ("hedef", "stop", "sure", "panik")]
    open_ = [s for s in every if s.status in OPEN_STATES]
    hits = sum(s.status == "hedef" for s in closed)
    pending = sum(s.status == PENDING and s.created == day for s in every)  # older ones can no longer be entered
    realized_value = CAPITAL + sum(s.notional * s.r for s in closed if s.r is not None)

    def pct(x):
        return f"%{x * 100:+.2f}".replace(".", ",")

    def tl(x):
        return f"{x:,.0f}".replace(",", ".") + " TL"

    def px(x):
        return f"{x:.2f}".replace(".", ",")

    rows, open_pnl, at_risk = [], 0.0, 0.0
    for s in open_:
        code = s.symbol.removesuffix(".IS")
        lots = f"{s.qty} lot, " if s.qty else ""
        if s.status == "bekliyor" or not s.entry_price:
            rows.append(f"  {code}: {lots}giriş ertesi açılışta (onay {s.created:%d.%m})")
            continue
        price = _last_price(bars, s.symbol)
        if price is None:
            rows.append(f"  {code}: {lots}giriş {px(s.entry_price)}, son fiyat yok")
            continue
        r = price / s.entry_price - 1
        open_pnl += s.notional * r
        to_stop = s.notional * (s.stop / s.entry_price - 1) if s.stop else None  # the result if the stop hits now
        at_risk += max(0.0, -(to_stop or 0.0))
        rows.append(f"  {code}: {lots}giriş {px(s.entry_price)} → son {px(price)} ({pct(r)}, {tl(s.notional * r)})")
        rows.append(f"     iz süren stop {px(s.stop)} (zirve {px(s.peak or s.entry_price)} − %{STOP * 100:.0f}), "
                    f"stopta sonuç {tl(to_stop or 0.0)}; kâr al {px(s.target)}")
    value = realized_value + open_pnl
    lines = [f"🧪 Sanal kasa: {tl(value)} ({pct(value / CAPITAL - 1)}); gerçekleşmiş {tl(realized_value)}, "
             f"açık pozisyonlar {tl(open_pnl)}",
             f"Açık sinyal {len(open_)}, kapanan {len(closed)}"
             + (f", hedefe ulaşan %{hits / len(closed) * 100:.0f}" if closed else "")
             + (f"; onay bekleyen kart {pending}" if pending else ""),
             *rows]
    if closed:  # K-70: winners and losers apart, against BIST 100 over the same days
        lines.append(performance_text(performance(conn, bars)))
    if open_:
        lines.append(f"Dinamik risk: bütün stoplar şimdi gelse kasanın %{at_risk / max(realized_value, 1) * 100:.2f}'i "
                     f"({tl(at_risk)}) gider.".replace(".", ",", 1))
    from core.signals import panic

    if panic.active():
        lines.append(f"⛔ Panik kilidi açık ({panic.since()}): takip ve taramalar durdu. Kaldırmak için /devam.")
    if blocked(conn, day):
        lines.append(f"⛔ Şalter açık: bugün kapanan işlemlerin zararı %{BREAKER * 100:.0f} sınırına ulaştı; "
                     "bugün tarama ve yeni sinyal yok.")
    return "\n".join(lines)


__all__ = ["BENCHMARK", "BREAKER", "BreakerTripped", "CAPITAL", "DISCLAIMER", "Performance", "SIZE", "Signal", "add",
           "blocked", "check_breaker", "connect", "equity", "locked", "performance", "performance_text", "realized",
           "signals", "summary", "update"]
