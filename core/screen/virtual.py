"""
QuantBIST
/tara_sanal: a saved screen or template run in a measurement-only virtual book (DECISIONS K-43).
Off by default; /tara_sanal AD turns it on for that name, with the criterion frozen at that moment.

Rules written before any result (görev /tara Aşama 4, kural 14), never tuned:
- each session's matches enter at the NEXT session's open, in alphabetical order, while fewer than
  MAX_POSITIONS are held; each takes 1/MAX_POSITIONS of the book's value at that open;
- a position leaves at the close HOLD sessions after entry, or at the first close at or below its
  stop (entry − STOP_ATR × ATR14 of the signal day), whichever comes first;
- commission and slippage both ways (the research costs), compared with XU100 over the same days.

The book is recomputed from the start date each time (prices only up to each day, no look-ahead)
and written nowhere: it never touches the personal paper orders (data/paper_orders.csv) or the
ledger. data/screen_virtual.csv only keeps the on/off rows (personal, append-only).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from core.config.paths import SCREEN_VIRTUAL_FILE
from core.infrastructure.csvfiles import open_append, read_rows
from core.screen.language import normalize, parse

VIRTUAL_FILE = SCREEN_VIRTUAL_FILE
COLUMNS = ("at", "name", "criteria", "action")
ON, OFF = "ac", "kapat"
MAX_BOOKS = 3
MAX_POSITIONS = 5
HOLD = 20
STOP_ATR = 2.0
COST = 0.0010 + 0.0005  # commission + slippage, each way (the research costs)
MIN_TRADES = 30
USAGE = "Kullanım: /tara_sanal AD (açar) · /tara_sanal AD kapat · /tara_sanal (durum)"
LABEL = "SANAL, yalnız ölçüm; gerçek ya da sanal emir verilmez"


@dataclass
class Trade:
    symbol: str
    entry_day: date
    entry: float
    stop: float
    exit_day: date | None = None
    exit: float | None = None
    reason: str = ""

    @property
    def result(self) -> float | None:
        if self.exit is None:
            return None
        return self.exit * (1 - COST) / (self.entry * (1 + COST)) - 1


@dataclass
class Book:
    start: date
    end: date | None = None
    trades: list[Trade] = field(default_factory=list)
    value: float = 1.0
    market: float | None = None  # XU100 over the same days

    @property
    def closed(self) -> list[Trade]:
        return [t for t in self.trades if t.exit is not None]

    @property
    def open(self) -> list[Trade]:
        return [t for t in self.trades if t.exit is None]


# --- on / off -------------------------------------------------------------------------------------


def books(path: Path | None = None) -> dict[str, tuple[str, date]]:
    """name -> (frozen criterion, start date) of the books that are on."""

    found: dict[str, tuple[str, date]] = {}
    for _, row in read_rows(Path(path or VIRTUAL_FILE), COLUMNS):
        if row["action"] == ON:
            found[row["name"]] = (row["criteria"], datetime.fromisoformat(row["at"]).date())
        else:
            found.pop(row["name"], None)
    return found


def _append(path: Path, name: str, criteria: str, action: str, now: datetime | None) -> None:
    from core.market.calendar import now_istanbul

    fh, new_file = open_append(path)
    with fh:
        writer = csv.writer(fh, lineterminator="\n")
        if new_file:
            writer.writerow(COLUMNS)
        writer.writerow([(now or now_istanbul()).isoformat(timespec="seconds"), name, criteria, action])


def command_text(words: list[str], path: Path | None = None, saved_path: Path | None = None,
                 now: datetime | None = None) -> str:
    from core.screen.subscriptions import criteria_of

    path = Path(path or VIRTUAL_FILE)
    current = books(path)
    if not words:
        if not current:
            return f"🧪 Sanal köprü kapalı (varsayılan). Açmak için: /tara_sanal AD\n{USAGE}"
        lines = [f"🧪 Sanal köprü ({LABEL}):"]
        lines += [f"  {name}: {criteria} · {start:%d.%m.%Y}'den beri" for name, (criteria, start) in sorted(current.items())]
        return "\n".join(lines + ["Sonuçlar: /performans", USAGE])
    name = normalize(words[0])
    if len(words) == 2 and normalize(words[1]) == OFF:
        if name not in current:
            return f"'{name}' için sanal köprü zaten kapalı."
        _append(path, name, current[name][0], OFF, now)
        return f"🧪 Sanal köprü kapatıldı: {name}. Geçmiş sonuç kaybolmaz; yeniden açılırsa yeni bir başlangıç olur."
    if len(words) != 1:
        return USAGE
    criteria = criteria_of(name, saved_path)
    if criteria is None:
        return f"⚠️ '{name}' adında kayıtlı tarama ya da şablon yok. {USAGE}"
    if name in current:
        return f"'{name}' sanal köprüsü zaten açık ({current[name][1]:%d.%m.%Y}'den beri)."
    if len(current) >= MAX_BOOKS:
        return f"⚠️ En fazla {MAX_BOOKS} sanal köprü açık olabilir."
    parse(criteria)
    _append(path, name, criteria, ON, now)
    return (f"🧪 Sanal köprü açıldı: {name} ({criteria}). Bir sonraki işlem gününden itibaren önceden yazılmış "
            f"kurallarla ölçülür: eşit ağırlık, en çok {MAX_POSITIONS} pozisyon, {HOLD} seans tutma, "
            f"{STOP_ATR:g} ATR stop, ertesi açılışta giriş. {LABEL}. Kişisel sanal emirlerine (/paper) dokunmaz.")


# --- the book -------------------------------------------------------------------------------------


def signals(query, frames: dict[str, pd.DataFrame], bench: pd.DataFrame) -> dict[str, pd.Series]:
    """symbol -> the days the query held (with its own liquidity floor)."""

    from core.screen import fields as F

    out = {}
    wanted = sorted(query.fields | {"islem_tl"})
    for symbol, df in frames.items():
        if df.empty:
            continue
        table = F.table(df, bench["close"], wanted)
        mask = query.mask(table)
        if query.liquidity > 0:
            mask &= table["islem_tl"] >= query.liquidity
        out[symbol] = mask.fillna(False).astype(bool)
    return out


def simulate(query, frames: dict[str, pd.DataFrame], bench: pd.DataFrame, start: date,
             end: date | None = None) -> Book:
    """The book from the first session after `start`: signals from `start` on, entries the next open."""

    from core.strategy.score import average_true_range

    days = bench.index[bench.index > pd.Timestamp(start)]
    if end is not None:
        days = days[days <= pd.Timestamp(end)]
    book = Book(start)
    if len(days) == 0:
        return book
    held = signals(query, frames, bench)
    atr = {s: average_true_range(df["high"], df["low"], df["close"], 14) for s, df in frames.items() if not df.empty}
    cash, shares, sessions = 1.0, {}, {}
    pending: list[tuple[str, float]] = []  # (symbol, stop distance) for the next open
    first = pd.Timestamp(start)
    for s, mask in held.items():  # the start day's own close can signal
        if first in mask.index and mask.loc[first] and not np.isnan(atr[s].get(first, np.nan)):
            pending.append((s, STOP_ATR * float(atr[s].loc[first])))
    for day in days:
        # entries at today's open
        value_open = cash + sum(n * float(frames[s].loc[day, "open"]) for s, n in shares.items()
                                if day in frames[s].index)
        for symbol, distance in sorted(pending):
            if len(shares) >= MAX_POSITIONS or symbol in shares or day not in frames[symbol].index:
                continue
            price = float(frames[symbol].loc[day, "open"])
            budget = min(value_open / MAX_POSITIONS, cash)
            if budget <= 0 or price <= 0:
                continue
            shares[symbol] = budget / (price * (1 + COST))
            cash -= budget
            sessions[symbol] = 0
            book.trades.append(Trade(symbol, day.date(), price, price - distance))
        pending = []
        # exits at today's close
        for trade in book.open:
            s = trade.symbol
            if s not in shares or day not in frames[s].index:
                continue
            sessions[s] += 1
            close = float(frames[s].loc[day, "close"])
            reason = "stop" if close <= trade.stop else ("süre" if sessions[s] >= HOLD else "")
            if reason:
                cash += shares.pop(s) * close * (1 - COST)
                trade.exit_day, trade.exit, trade.reason = day.date(), close, reason
        # signals at today's close, for tomorrow's open
        for s, mask in held.items():
            if day in mask.index and mask.loc[day] and s not in shares:
                distance = atr[s].get(day, np.nan)
                if not np.isnan(distance):
                    pending.append((s, STOP_ATR * float(distance)))
        book.end = day.date()
    last = days[-1]
    book.value = cash + sum(n * float(frames[s]["close"].loc[:last].iloc[-1]) for s, n in shares.items())
    base = bench["close"].loc[:pd.Timestamp(start)]
    if len(base):
        book.market = float(bench["close"].loc[last]) / float(base.iloc[-1]) - 1
    return book


def report_lines(path: Path | None = None, live=None, today: date | None = None) -> list[str]:
    """The /performans section; empty-handed when every book is off (the default)."""

    from core.reports.daily import pct
    from core.screen import universe
    from core.screen.command import _live

    current = books(path)
    lines = ["", f"🧪 Sanal köprü ({LABEL})"]
    if not current:
        return lines + ["  Kapalı (varsayılan). /tara_sanal AD ile bir tarama ölçülmeye başlar."]
    for name, (criteria, start) in sorted(current.items()):
        try:
            query = parse(criteria)
            frames, bench = (live or _live)(universe.symbols(query.universe))
            book = simulate(query, frames, bench, start, today)
        except Exception as exc:  # noqa: BLE001 - one book never hides the others
            lines.append(f"  {name}: hesaplanamadı ({exc})")
            continue
        head = f"  {name} ({criteria}), {start:%d.%m.%Y}'den beri"
        if book.end is None:
            lines.append(f"{head}: henüz işlem günü yok.")
            continue
        closed = [t.result for t in book.closed]
        market = "—" if book.market is None else pct(book.market)
        lines.append(f"{head}: kitap {pct(book.value - 1)}, XU100 {market}; {len(book.open)} açık, "
                     f"{len(closed)} kapanmış işlem")
        if len(closed) < MIN_TRADES:
            lines.append(f"    veri birikiyor ({len(closed)}/{MIN_TRADES} kapanmış işlem); karar için kullanılmaz")
        else:
            lines.append(f"    işlem ortalaması {pct(float(np.mean(closed)))}, isabet %"
                         f"{100 * float(np.mean([r > 0 for r in closed])):.0f}; kanıt değildir")
    return lines


__all__ = ["Book", "HOLD", "MAX_POSITIONS", "STOP_ATR", "Trade", "books", "command_text", "report_lines", "simulate"]
