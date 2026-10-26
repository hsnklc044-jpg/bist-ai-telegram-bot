"""
QuantBIST
Texts and actions behind the Telegram portfolio commands
(kept free of Telegram imports so they can be tested).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from core.alerts import open_alerts
from core.alerts.rules import SEVERITY
from core.config.paths import ALERTS_LOG_FILE, LEDGER_FILE, PAPER_ORDERS_FILE
from core.config.trading import COMMISSION
from core.ledger.book import Entry, append_entry, cash_balance, load_ledger, open_positions
from core.ledger.commands import PaperCommand, TradeCommand
from core.ledger.paper import cancel_order, load_orders, place_order
from core.market.calendar import now_istanbul
from core.reports.daily import ACCOUNT_NAMES, pct, raw_bars, tr

SIDE_NAMES = {"buy": "alış", "sell": "satış", "bonus": "bedelsiz", "rights": "bedelli"}


def record_trade(cmd: TradeCommand, ledger_path: Path | str | None = None, today: date | None = None) -> str:
    today = today or now_istanbul().date()
    fee = cmd.fee
    if fee is None:
        fee = round(cmd.quantity * cmd.price * COMMISSION, 2) if cmd.side in ("buy", "sell") else 0.0
    entry = append_entry(
        Entry(cmd.day or today, "real", cmd.symbol, cmd.side, cmd.quantity, cmd.price, fee, "telegram"),
        ledger_path or LEDGER_FILE,
        today=today,
    )
    return (
        f"✅ Deftere yazıldı (#{entry.id}): {entry.date:%d.%m.%Y} {SIDE_NAMES[entry.side]} "
        f"{entry.symbol.removesuffix('.IS')} {tr(entry.quantity)} adet × {tr(entry.price, 2)} TL, "
        f"komisyon {tr(entry.fee, 2)} TL\nYanlışsa ters işlemle düzeltin (defter silinmez)."
    )


def portfolio_text(ledger_path: Path | str | None = None) -> str:
    entries = load_ledger(ledger_path or LEDGER_FILE)
    lines = ["💼 Portföy (son kapanış fiyatlarıyla)"]
    for account in ("real", "paper"):
        positions = open_positions(entries, account)
        if account == "real" and not positions:
            continue
        invested = 0.0
        rows = []
        for p in positions:
            bars = raw_bars(p.symbol)
            price = float(bars["close"].iloc[-1]) if not bars.empty else float("nan")
            value = p.quantity * price
            invested += value
            pnl = value - p.cost
            rows.append(
                f"  {p.symbol.removesuffix('.IS')}: {tr(p.quantity)} adet, maliyet {tr(p.average_cost, 2)}, "
                f"son {tr(price, 2)} → {'+' if pnl >= 0 else '-'}{tr(abs(pnl))} TL ({pct(pnl / p.cost if p.cost else 0)})"
            )
        lines += ["", ACCOUNT_NAMES[account]]
        if account == "paper":
            cash = cash_balance(entries, "paper")
            lines.append(f"  Nakit {tr(cash)} TL, hisse {tr(invested)} TL, toplam {tr(cash + invested)} TL")
        lines += rows or ["  Açık pozisyon yok."]
        realized = sum(p.realized for (acc, _), p in _all(entries).items() if acc == account)
        if realized:
            lines.append(f"  Gerçekleşen kâr/zarar: {'+' if realized >= 0 else '-'}{tr(abs(realized))} TL")
    return "\n".join(lines)


def _all(entries):
    from core.ledger.book import replay

    return replay(entries)


def paper_action(
    cmd: PaperCommand,
    orders_path: Path | str | None = None,
    ledger_path: Path | str | None = None,
    now=None,
) -> str:
    orders_path = orders_path or PAPER_ORDERS_FILE
    if cmd.action == "cancel":
        o = cancel_order(cmd.order_id, orders_path)
        return f"🗑 Sanal emir #{o.id} iptal edildi."
    if cmd.action == "order":
        o = place_order(cmd.symbol, cmd.side, cmd.quantity, now=now, orders_path=orders_path,
                        ledger_path=ledger_path or LEDGER_FILE)
        verb = "alış" if o.side == "buy" else "satış"
        return (
            f"📝 Sanal {verb} emri #{o.id}: {o.symbol.removesuffix('.IS')} {tr(o.quantity)} adet.\n"
            "Bir sonraki açılış fiyatından (09:40 öncesi verilen emir aynı gün; komisyon ve kayma dahil) dolacak; "
            "kilitli tavan/taban gününde beklenir. Gerçek emir gönderilmez."
        )
    pending = [o for o in load_orders(orders_path) if o.status == "pending"]
    if not pending:
        return "Bekleyen sanal emir yok.\n\n" + _usage()
    lines = ["⏳ Bekleyen sanal emirler"]
    for o in pending:
        verb = "al" if o.side == "buy" else "sat"
        lines.append(f"  #{o.id} {verb} {o.symbol.removesuffix('.IS')} {tr(o.quantity)} adet ({o.created_at:%d.%m.%Y %H:%M})")
    return "\n".join(lines)


def _usage() -> str:
    from core.ledger.commands import PAPER_USAGE

    return PAPER_USAGE


def alerts_text(alerts_path: Path | str | None = None) -> str:
    current = open_alerts(alerts_path or ALERTS_LOG_FILE)
    if not current:
        return "✅ Açık risk uyarısı yok."
    lines = ["⚠️ Açık risk uyarıları"]
    for (account, symbol, _rule), row in sorted(current.items(), key=lambda kv: -int(kv[1]["severity"])):
        lines.append(
            f"  [{SEVERITY[int(row['severity'])]}] {ACCOUNT_NAMES[account]} – {symbol.removesuffix('.IS')}: "
            f"{row['message']} (veri {row['data_date']})"
        )
    return "\n".join(lines)


__all__ = ["record_trade", "portfolio_text", "paper_action", "alerts_text"]
