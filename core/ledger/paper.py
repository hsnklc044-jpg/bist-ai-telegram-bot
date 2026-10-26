"""
QuantBIST
Paper (simulated) orders. No order ever reaches a broker.

An order fills at the OPEN of the first session that starts after it
was placed: the same day if it was placed before the opening auction
(09:40 Istanbul), otherwise the next session; the same rule as the
backtest, with commission and slippage. Only final candles are used. A buy on a locked limit-up day
or a sell on a locked limit-down day does not fill; it waits for the
next session. Fills are written to the ledger as account "paper".

    data/paper_orders.csv   id,created_at,symbol,side,quantity,status,fill_date,fill_price,note
    status: pending | filled | rejected | cancelled
"""

from __future__ import annotations

import csv
from collections.abc import Callable
from dataclasses import asdict, dataclass, replace
from datetime import date, datetime, time
from pathlib import Path

import pandas as pd

from core.backtest.engine import LIMIT_MOVE
from core.config.paths import LEDGER_FILE, PAPER_ORDERS_FILE
from core.config.trading import COMMISSION, SLIPPAGE
from core.ledger.book import Entry, LedgerError, append_entry, load_ledger, replay
from core.market.calendar import ISTANBUL, now_istanbul
from core.market.symbols import normalize_symbol

OPENING_AUCTION = time(9, 40)  # BIST opening session starts; later orders wait for the next day

FIELDS = ("id", "created_at", "symbol", "side", "quantity", "status", "fill_date", "fill_price", "note")


@dataclass(frozen=True)
class Order:
    id: int
    created_at: datetime
    symbol: str
    side: str
    quantity: float
    status: str = "pending"
    fill_date: date | None = None
    fill_price: float | None = None
    note: str = ""


def load_orders(path: Path | str | None = None) -> list[Order]:
    path = Path(path or PAPER_ORDERS_FILE)
    if not path.exists():
        return []
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return [
            Order(
                id=int(r["id"]),
                created_at=datetime.fromisoformat(r["created_at"]),
                symbol=r["symbol"],
                side=r["side"],
                quantity=float(r["quantity"]),
                status=r["status"],
                fill_date=date.fromisoformat(r["fill_date"]) if r["fill_date"] else None,
                fill_price=float(r["fill_price"]) if r["fill_price"] else None,
                note=r.get("note") or "",
            )
            for r in csv.DictReader(fh)
        ]


def save_orders(orders: list[Order], path: Path | str | None = None) -> None:
    path = Path(path or PAPER_ORDERS_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, FIELDS, lineterminator="\n")
        writer.writeheader()
        for o in orders:
            row = asdict(o)
            row["created_at"] = o.created_at.isoformat(timespec="seconds")
            row["quantity"] = f"{o.quantity:.10g}"
            row["fill_date"] = o.fill_date.isoformat() if o.fill_date else ""
            row["fill_price"] = f"{o.fill_price:.10g}" if o.fill_price is not None else ""
            writer.writerow(row)
    tmp.replace(path)


def place_order(
    symbol: str,
    side: str,
    quantity: float,
    now: datetime | None = None,
    orders_path: Path | str | None = None,
    ledger_path: Path | str | None = None,
) -> Order:
    side = side.lower()
    if side not in ("buy", "sell"):
        raise LedgerError("emir türü al ya da sat olmalı")
    if not quantity > 0:
        raise LedgerError("adet sıfırdan büyük olmalı")
    symbol = normalize_symbol(symbol)
    orders = load_orders(orders_path)

    if side == "sell":
        held = replay(load_ledger(ledger_path or LEDGER_FILE)).get(("paper", symbol))
        held_qty = held.quantity if held else 0.0
        pending = sum(o.quantity for o in orders if o.status == "pending" and o.side == "sell" and o.symbol == symbol)
        if quantity > held_qty - pending + 1e-9:
            raise LedgerError(f"sanal hesapta {symbol} için satılabilir adet {held_qty - pending:g}")

    order = Order(
        id=max((o.id for o in orders), default=0) + 1,
        created_at=(now or now_istanbul()).astimezone(ISTANBUL),
        symbol=symbol,
        side=side,
        quantity=float(quantity),
    )
    save_orders([*orders, order], orders_path)
    return order


def cancel_order(order_id: int, orders_path: Path | str | None = None) -> Order:
    orders = load_orders(orders_path)
    for i, o in enumerate(orders):
        if o.id == order_id:
            if o.status != "pending":
                raise LedgerError(f"emir {order_id} zaten {o.status}")
            orders[i] = replace(o, status="cancelled", note="kullanıcı iptal etti")
            save_orders(orders, orders_path)
            return orders[i]
    raise LedgerError(f"emir bulunamadı: {order_id}")


def _locked(df: pd.DataFrame, day: pd.Timestamp, side: str) -> bool:
    i = df.index.get_loc(day)
    if i == 0:
        return False
    bar, prev_close = df.iloc[i], df["close"].iloc[i - 1]
    if bar["high"] > bar["low"]:
        return False
    change = bar["close"] / prev_close - 1
    return change >= LIMIT_MOVE if side == "buy" else change <= -LIMIT_MOVE


def fill_pending(
    bars: Callable[[str], pd.DataFrame],
    orders_path: Path | str | None = None,
    ledger_path: Path | str | None = None,
) -> list[Order]:
    """
    Fill every pending order whose fill session is available.
    `bars(symbol)` returns FINAL raw daily candles (open, high, low, close).
    Returns the orders whose status changed.
    """

    orders = load_orders(orders_path)
    changed: list[Order] = []

    for i, o in enumerate(orders):
        if o.status != "pending":
            continue
        df = bars(o.symbol)
        if df is None or df.empty:
            continue
        created = o.created_at.astimezone(ISTANBUL)
        placed = pd.Timestamp(created.date())
        first = df.index >= placed if created.time() < OPENING_AUCTION else df.index > placed
        for day in df.index[first]:
            if _locked(df, day, o.side):
                continue
            open_ = float(df.at[day, "open"])
            price = open_ * (1 + SLIPPAGE) if o.side == "buy" else open_ * (1 - SLIPPAGE)
            fee = price * o.quantity * COMMISSION
            try:
                append_entry(
                    Entry(day.date(), "paper", o.symbol, o.side, o.quantity, price, fee, f"sanal emir #{o.id}"),
                    ledger_path,
                )
                orders[i] = replace(o, status="filled", fill_date=day.date(), fill_price=price)
            except LedgerError as exc:
                orders[i] = replace(o, status="rejected", fill_date=day.date(), note=str(exc))
            changed.append(orders[i])
            break

    if changed:
        save_orders(orders, orders_path)
    return changed


__all__ = ["Order", "load_orders", "save_orders", "place_order", "cancel_order", "fill_pending"]
