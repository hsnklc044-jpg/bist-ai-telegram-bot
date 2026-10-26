"""
QuantBIST
Paper (simulated) orders. No order ever reaches a broker.

An order fills at the OPEN of the first session that starts after it
was placed: the same day if it was placed before the opening auction
(09:40 Istanbul), otherwise the next session; the same rule as the
backtest, with commission and slippage. Only final candles are used. A buy on a locked limit-up day
or a sell on a locked limit-down day does not fill; it waits for the
next session. Fills are written to the ledger as account "paper".

    data/paper_orders.csv   id,created_at,symbol,side,quantity,status,fill_date,fill_price,note,
                            reason,data_date,ref_close,score,view,est_value,account_share,
                            atr_pct,fill_open,fee,fill_log
    status: pending | filled | rejected | cancelled

The columns after `note` (v0.28.0) record why and on which data the
order was given, its size and volatility at that moment, and how it was
filled (open before slippage, commission, days it could not fill). They
are appended at the end: files written before v0.28.0 load unchanged
with these fields empty, and older code ignores them when reading.

A fill is written to the ledger with the note "sanal emir #<id>". If
that entry already exists (the run stopped after writing the ledger but
before saving the orders), the order is marked filled from it instead of
being filled twice.
"""

from __future__ import annotations

import csv
import shutil
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

FIELDS = (
    "id", "created_at", "symbol", "side", "quantity", "status", "fill_date", "fill_price", "note",
    "reason", "data_date", "ref_close", "score", "view", "est_value", "account_share", "atr_pct",
    "fill_open", "fee", "fill_log",
)
FLOAT_FIELDS = ("ref_close", "score", "est_value", "account_share", "atr_pct", "fill_open", "fee")


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
    reason: str = ""  # the user's own reason, as typed
    data_date: date | None = None  # last final candle when the order was given
    ref_close: float | None = None  # its close (raw price)
    score: float | None = None  # technical score then (no proven predictive power)
    view: str = ""
    est_value: float | None = None  # quantity x ref_close
    account_share: float | None = None  # est_value / paper account value then
    atr_pct: float | None = None  # 14-day ATR / close: typical daily move
    fill_open: float | None = None  # opening price before slippage
    fee: float | None = None
    fill_log: str = ""  # sessions it could not fill, duplicate guard notes


def _float(text: str | None) -> float | None:
    return float(text) if text not in (None, "") else None


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
                reason=r.get("reason") or "",
                data_date=date.fromisoformat(r["data_date"]) if r.get("data_date") else None,
                view=r.get("view") or "",
                fill_log=r.get("fill_log") or "",
                **{k: _float(r.get(k)) for k in FLOAT_FIELDS},
            )
            for r in csv.DictReader(fh)
        ]


def _keep_old_format(path: Path) -> None:
    """Before the first rewrite of a pre-v0.28 file, keep an exact copy next to it."""

    if not path.exists():
        return
    with open(path, encoding="utf-8-sig", newline="") as fh:
        header = next(csv.reader(fh), [])
    copy = path.with_name(f"{path.stem}_before_v0.28{path.suffix}")
    if tuple(header) != FIELDS and not copy.exists():
        shutil.copy2(path, copy)


def save_orders(orders: list[Order], path: Path | str | None = None) -> None:
    path = Path(path or PAPER_ORDERS_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    _keep_old_format(path)
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
            row["data_date"] = o.data_date.isoformat() if o.data_date else ""
            for k in FLOAT_FIELDS:
                row[k] = f"{row[k]:.10g}" if row[k] is not None else ""
            writer.writerow(row)
    tmp.replace(path)


def place_order(
    symbol: str,
    side: str,
    quantity: float,
    now: datetime | None = None,
    orders_path: Path | str | None = None,
    ledger_path: Path | str | None = None,
    reason: str = "",
    snapshot: dict | None = None,
) -> Order:
    """`snapshot` (from order_snapshot) records the data and risk at this moment."""

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
        reason=" ".join(reason.split())[:200],
        **{k: v for k, v in (snapshot or {}).items() if k != "account_value"},
    )
    if order.ref_close is not None:
        order = replace(order, est_value=order.quantity * order.ref_close)
        if snapshot and snapshot.get("account_value"):
            order = replace(order, account_share=order.est_value / snapshot["account_value"])
    save_orders([*orders, order], orders_path)
    return order


def order_snapshot(
    symbol: str,
    raw: Callable[[str], pd.DataFrame],
    adjusted: Callable[[str], pd.DataFrame],
    account_value: float | None,
) -> dict:
    """
    Data and risk at the moment of the order: last final candle, its raw
    close, the technical score and view, and ATR as a share of price.
    Missing data leaves fields empty; it never blocks the order.
    """

    from core.config.thresholds import SIGNAL_VIEW_LABELS
    from core.strategy.score import score_frame

    out: dict = {"account_value": account_value}
    symbol = normalize_symbol(symbol)
    try:
        bars = raw(symbol)
        if bars is not None and not bars.empty:
            out["data_date"] = bars.index[-1].date()
            out["ref_close"] = float(bars["close"].iloc[-1])
        frame = adjusted(symbol)
        if frame is not None and len(frame) > 60:
            last = score_frame(frame).iloc[-1]
            if pd.notna(last["score"]):
                out["score"] = float(last["score"])
                out["view"] = SIGNAL_VIEW_LABELS.get(last["signal"], str(last["signal"]))
            if pd.notna(last["volatility"]):
                out["atr_pct"] = float(last["volatility"])
    except Exception:  # noqa: BLE001 - a snapshot problem must not block the order
        pass
    return out


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


def _add_log(log: str, note: str) -> str:
    return f"{log}; {note}" if log else note


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
    dirty = False
    booked = {e.note: e for e in load_ledger(ledger_path) if e.account == "paper" and e.note.startswith("sanal emir #")}

    for i, o in enumerate(orders):
        if o.status != "pending":
            continue
        tag = f"sanal emir #{o.id}"
        if tag in booked:
            e = booked[tag]
            orders[i] = replace(
                o, status="filled", fill_date=e.date, fill_price=e.price, fee=e.fee,
                fill_log=_add_log(o.fill_log, "defterde zaten vardı; ikinci kez yazılmadı"),
            )
            changed.append(orders[i])
            continue
        df = bars(o.symbol)
        if df is None or df.empty:
            continue
        created = o.created_at.astimezone(ISTANBUL)
        placed = pd.Timestamp(created.date())
        first = df.index >= placed if created.time() < OPENING_AUCTION else df.index > placed
        for day in df.index[first]:
            if _locked(df, day, o.side):
                note = f"{day:%d.%m.%Y} {'tavan' if o.side == 'buy' else 'taban'} kilidi, dolmadı"
                if note not in o.fill_log:
                    o = orders[i] = replace(o, fill_log=_add_log(o.fill_log, note))
                    dirty = True
                continue
            open_ = float(df.at[day, "open"])
            price = open_ * (1 + SLIPPAGE) if o.side == "buy" else open_ * (1 - SLIPPAGE)
            fee = price * o.quantity * COMMISSION
            try:
                append_entry(
                    Entry(day.date(), "paper", o.symbol, o.side, o.quantity, price, fee, tag),
                    ledger_path,
                )
                orders[i] = replace(
                    o, status="filled", fill_date=day.date(), fill_price=price, fill_open=open_, fee=fee
                )
            except LedgerError as exc:
                orders[i] = replace(o, status="rejected", fill_date=day.date(), note=str(exc))
            changed.append(orders[i])
            break

    if changed or dirty:
        save_orders(orders, orders_path)
    return changed


__all__ = ["Order", "load_orders", "save_orders", "place_order", "cancel_order", "fill_pending", "order_snapshot"]
