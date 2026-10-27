"""
QuantBIST
Ledger file handling and FIFO position accounting.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field, replace
from datetime import date
from pathlib import Path

from core.config.paths import LEDGER_FILE
from core.config.trading import ACCOUNTS, PAPER_INITIAL_CAPITAL
from core.infrastructure.csvfiles import read_rows
from core.infrastructure.exceptions import PersonalFileError
from core.market.symbols import normalize_symbol

COLUMNS = ("id", "date", "account", "symbol", "side", "quantity", "price", "fee", "note")
SIDES = ("buy", "sell", "bonus", "rights", "dividend")  # dividend: quantity = shares paid on, price = net per share
EPS = 1e-9


class LedgerError(ValueError):
    """A ledger row is invalid or would break the books (e.g. selling more than held)."""


class LedgerFileError(PersonalFileError, LedgerError):
    """ledger.csv itself cannot be read (damaged or cut-off row)."""


@dataclass(frozen=True)
class Entry:
    date: date
    account: str
    symbol: str
    side: str
    quantity: float
    price: float
    fee: float = 0.0
    note: str = ""
    id: int | None = None

    def validate(self, today: date | None = None) -> Entry:
        if self.account not in ACCOUNTS:
            raise LedgerError(f"hesap 'real' ya da 'paper' olmalı: {self.account!r}")
        if self.side not in SIDES:
            raise LedgerError(f"işlem türü {SIDES} olmalı: {self.side!r}")
        if not self.quantity > 0:
            raise LedgerError(f"adet sıfırdan büyük olmalı: {self.quantity}")
        if self.side in ("buy", "sell", "rights", "dividend") and not self.price > 0:
            raise LedgerError(f"fiyat sıfırdan büyük olmalı: {self.price}")
        if self.side == "dividend" and self.fee:
            raise LedgerError("temettüde komisyon yazılmaz; pay başına net (stopaj düşülmüş) tutarı girin")
        if self.side == "bonus" and self.price != 0:
            raise LedgerError("bedelsiz payın fiyatı 0 olmalı")
        if self.fee < 0:
            raise LedgerError(f"komisyon negatif olamaz: {self.fee}")
        if today is not None and self.date > today:
            raise LedgerError(f"gelecek tarihli işlem: {self.date}")
        return replace(self, symbol=normalize_symbol(self.symbol))

    @property
    def amount(self) -> float:
        """Cash effect: negative for money paid out."""

        if self.side in ("sell", "dividend"):
            return self.quantity * self.price - self.fee
        if self.side == "bonus":
            return 0.0
        return -(self.quantity * self.price + self.fee)


@dataclass
class Lot:
    quantity: float
    unit_cost: float  # including the buy fee
    opened: date


@dataclass
class Position:
    account: str
    symbol: str
    lots: list[Lot] = field(default_factory=list)
    realized: float = 0.0
    fees: float = 0.0

    @property
    def quantity(self) -> float:
        return sum(lot.quantity for lot in self.lots)

    @property
    def cost(self) -> float:
        return sum(lot.quantity * lot.unit_cost for lot in self.lots)

    @property
    def average_cost(self) -> float:
        q = self.quantity
        return self.cost / q if q > EPS else 0.0

    @property
    def opened(self) -> date | None:
        """Date of the oldest open lot (used for 'highest close since entry')."""

        return min((lot.opened for lot in self.lots), default=None)

    def apply(self, e: Entry) -> None:
        self.fees += e.fee
        if e.side == "buy" or e.side == "rights":
            self.lots.append(Lot(e.quantity, (e.quantity * e.price + e.fee) / e.quantity, e.date))
        elif e.side == "bonus":
            held = self.quantity
            if held <= EPS:
                raise LedgerError(f"{e.date} {e.symbol}: elde pay yokken bedelsiz pay girilemez")
            ratio = (held + e.quantity) / held
            for lot in self.lots:
                lot.quantity *= ratio
                lot.unit_cost /= ratio
        elif e.side == "dividend":
            # cash income on shares held that day; the lots and their cost stay as they are
            if e.quantity > self.quantity + EPS:
                raise LedgerError(
                    f"{e.date} {e.symbol} ({e.account}): {e.quantity:g} pay için temettü girilemez, "
                    f"elde {self.quantity:g} adet var"
                )
            self.realized += e.quantity * e.price
        elif e.side == "sell":
            if e.quantity > self.quantity + EPS:
                raise LedgerError(
                    f"{e.date} {e.symbol} ({e.account}): {e.quantity:g} adet satılamaz, "
                    f"elde {self.quantity:g} adet var"
                )
            remaining = e.quantity
            cost = 0.0
            while remaining > EPS:
                lot = self.lots[0]
                take = min(lot.quantity, remaining)
                cost += take * lot.unit_cost
                lot.quantity -= take
                remaining -= take
                if lot.quantity <= EPS:
                    self.lots.pop(0)
            self.realized += e.quantity * e.price - e.fee - cost


def _ordered(entries: list[Entry]) -> list[Entry]:
    return sorted(entries, key=lambda e: (e.date, e.id if e.id is not None else 10**12))


def replay(entries: list[Entry], as_of: date | None = None) -> dict[tuple[str, str], Position]:
    """All positions (open and closed) after applying the entries in date order."""

    books: dict[tuple[str, str], Position] = {}
    for e in _ordered(entries):
        if as_of is not None and e.date > as_of:
            continue
        key = (e.account, e.symbol)
        books.setdefault(key, Position(e.account, e.symbol)).apply(e)
    return books


def open_positions(entries: list[Entry], account: str | None = None, as_of: date | None = None):
    return [
        p
        for (acc, _), p in sorted(replay(entries, as_of).items())
        if p.quantity > EPS and (account is None or acc == account)
    ]


def cash_balance(entries: list[Entry], account: str = "paper", as_of: date | None = None) -> float:
    """Cash of an account. The paper account starts with PAPER_INITIAL_CAPITAL."""

    start = PAPER_INITIAL_CAPITAL if account == "paper" else 0.0
    return start + sum(
        e.amount for e in entries if e.account == account and (as_of is None or e.date <= as_of)
    )


# ---------------------------------------------------------------------------
# File
# ---------------------------------------------------------------------------


def _parse(row: dict, line: int, path: Path) -> Entry:
    try:
        return Entry(
            id=int(row["id"]),
            date=date.fromisoformat(row["date"].strip()),
            account=row["account"].strip().lower(),
            symbol=row["symbol"].strip(),
            side=row["side"].strip().lower(),
            quantity=float(row["quantity"]),
            price=float(row["price"]),
            fee=float(row.get("fee") or 0),
            note=(row.get("note") or "").strip(),
        ).validate()
    except (KeyError, ValueError, TypeError, AttributeError) as exc:
        raise LedgerFileError(path, str(exc), line=line) from exc


def load_ledger(path: Path | str | None = None) -> list[Entry]:
    """All rows; a bad row stops loading with its line number (never skipped silently)."""

    path = Path(path or LEDGER_FILE)
    try:
        rows = read_rows(path, COLUMNS)
    except PersonalFileError as exc:
        raise LedgerFileError(exc.path, exc.reason, exc.line) from exc
    entries = [_parse(row, line, path) for line, row in rows]
    ids = [e.id for e in entries]
    if len(ids) != len(set(ids)):
        raise LedgerError(f"{path}: aynı id birden fazla kez geçiyor")
    replay(entries)  # raises on an impossible history (e.g. overselling)
    return entries


def append_entry(entry: Entry, path: Path | str | None = None, today: date | None = None) -> Entry:
    """Validate, check the books stay consistent, then append. Returns the stored entry."""

    path = Path(path or LEDGER_FILE)
    entries = load_ledger(path)
    entry = entry.validate(today)
    entry = replace(entry, id=max((e.id for e in entries), default=0) + 1)
    replay([*entries, entry])
    if entry.account == "paper" and entry.side in ("buy", "rights"):
        if cash_balance([*entries, entry], "paper") < -EPS:
            raise LedgerError("sanal hesapta yeterli nakit yok")

    new_file = not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        if new_file:
            writer.writerow(COLUMNS)
        writer.writerow(
            [
                entry.id,
                entry.date.isoformat(),
                entry.account,
                entry.symbol,
                entry.side,
                f"{entry.quantity:.10g}",
                f"{entry.price:.10g}",
                f"{entry.fee:.4f}",
                entry.note,
            ]
        )
    return entry
