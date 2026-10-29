"""
QuantBIST
Texts and actions behind the Telegram portfolio commands
(kept free of Telegram imports so they can be tested).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from core.alerts import open_alerts
from core.alerts.portfolio import portfolio_risk
from core.alerts.rules import SEVERITY
from core.config.paths import ALERTS_LOG_FILE, LEDGER_FILE, PAPER_ORDERS_FILE
from core.config.trading import COMMISSION
from core.ledger.book import Entry, append_entry, cash_balance, load_ledger
from core.ledger.commands import PaperCommand, TradeCommand
from core.ledger.paper import cancel_order, load_orders, order_snapshot, place_order
from core.market.calendar import now_istanbul
from core.market.universe import BENCHMARK
from core.reports.daily import ACCOUNT_NAMES, adjusted_bars, pct, raw_bars, tr

SIDE_NAMES = {"buy": "alış", "sell": "satış", "bonus": "bedelsiz", "rights": "bedelli", "dividend": "temettü"}


def _exclusive():
    """
    The ledger and the paper orders are read, checked and rewritten. The
    daily report does the same while filling orders, so commands take the
    same lock: a write can never overwrite another one.
    """

    from core.reports.runs import report_lock

    return report_lock()


def _busy_text(exc) -> str:
    return f"⏳ {exc} İşleminiz kaydedilmedi; birkaç dakika sonra tekrar deneyin."


def record_trade(cmd: TradeCommand, ledger_path: Path | str | None = None, today: date | None = None) -> str:
    from core.reports.runs import ReportBusy

    try:
        with _exclusive():
            return _record_trade(cmd, ledger_path, today)
    except ReportBusy as exc:
        return _busy_text(exc)


def _record_trade(cmd: TradeCommand, ledger_path: Path | str | None = None, today: date | None = None) -> str:
    today = today or now_istanbul().date()
    fee = cmd.fee
    if fee is None:
        fee = round(cmd.quantity * cmd.price * COMMISSION, 2) if cmd.side in ("buy", "sell") else 0.0
    entry = append_entry(
        Entry(cmd.day or today, cmd.account, cmd.symbol, cmd.side, cmd.quantity, cmd.price, fee, "telegram"),
        ledger_path or LEDGER_FILE,
        today=today,
    )
    return (
        f"✅ Deftere yazıldı (#{entry.id}){' – Sanal hesap' if entry.account == 'paper' else ''}: "
        f"{entry.date:%d.%m.%Y} {SIDE_NAMES[entry.side]} "
        f"{entry.symbol.removesuffix('.IS')} {tr(entry.quantity)} adet × {tr(entry.price, 2)} TL, "
        f"komisyon {tr(entry.fee, 2)} TL\nYanlışsa ters işlemle düzeltin (defter silinmez)."
    )


def portfolio_text(ledger_path: Path | str | None = None) -> str:
    from core.reports.daily import value_holdings

    entries = load_ledger(ledger_path or LEDGER_FILE)
    bench = raw_bars(BENCHMARK)
    latest = bench.index[-1].date() if not bench.empty else None
    lines = ["💼 Portföy (son kapanış fiyatlarıyla)"]
    for account in ("real", "paper"):
        holdings, invested = value_holdings(entries, account)
        if account == "real" and not holdings:
            continue
        rows = []
        values = {}
        for h in holdings:
            p = h.position
            values[p.symbol] = h.value
            pnl = h.value - p.cost
            # an old price is named with its date, never shown as today's close
            dated = f" ({h.price_day:%d.%m} tarihli)" if latest and h.price_day and h.price_day < latest else ""
            rows.append(
                f"  {p.symbol.removesuffix('.IS')}: {tr(p.quantity)} adet, maliyet {tr(p.average_cost, 2)}, "
                f"son {tr(h.price, 2)}{dated} → {'+' if pnl >= 0 else '-'}{tr(abs(pnl))} TL "
                f"({pct(pnl / p.cost if p.cost else 0)})"
            )
        lines += ["", ACCOUNT_NAMES[account]]
        if account == "paper":
            cash = cash_balance(entries, "paper")
            lines.append(f"  Nakit {tr(cash)} TL, hisse {tr(invested)} TL, toplam {tr(cash + invested)} TL")
        lines += rows or ["  Açık pozisyon yok."]
        if values:
            total = invested + (cash_balance(entries, "paper") if account == "paper" else 0.0)
            risk = portfolio_risk(values, {sym: adjusted_bars(sym) for sym in values}, total)
            lines.append(f"  {risk.line()}")
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
    if cmd.action in ("cancel", "order"):
        from core.reports.runs import ReportBusy

        try:
            with _exclusive():
                return _paper_write(cmd, orders_path, ledger_path, now)
        except ReportBusy as exc:
            return _busy_text(exc)
    pending = [o for o in load_orders(orders_path) if o.status == "pending"]
    if not pending:
        return "Bekleyen sanal emir yok.\n\n" + _usage()
    lines = ["⏳ Bekleyen sanal emirler"]
    for o in pending:
        verb = "al" if o.side == "buy" else "sat"
        lines.append(f"  #{o.id} {verb} {o.symbol.removesuffix('.IS')} {tr(o.quantity)} adet ({o.created_at:%d.%m.%Y %H:%M})")
        if o.reason:
            lines.append(f"     gerekçe: {o.reason}")
        if o.fill_log:
            lines.append(f"     {o.fill_log}")
    return "\n".join(lines)


def _paper_write(cmd: PaperCommand, orders_path, ledger_path, now) -> str:
    if cmd.action == "cancel":
        o = cancel_order(cmd.order_id, orders_path)
        return f"🗑 Sanal emir #{o.id} iptal edildi."
    if cmd.action == "order":
        ledger_path = ledger_path or LEDGER_FILE
        snapshot = order_snapshot(cmd.symbol, raw_bars, adjusted_bars, _paper_value(ledger_path))
        o = place_order(cmd.symbol, cmd.side, cmd.quantity, now=now, orders_path=orders_path,
                        ledger_path=ledger_path, reason=cmd.reason, snapshot=snapshot)
        verb = "alış" if o.side == "buy" else "satış"
        return (
            f"📝 Sanal {verb} emri #{o.id}: {o.symbol.removesuffix('.IS')} {tr(o.quantity)} adet.\n"
            "Bir sonraki açılış fiyatından (09:40 öncesi verilen emir aynı gün; komisyon ve kayma dahil) dolacak; "
            "kilitli tavan/taban gününde beklenir. Gerçek emir gönderilmez.\n\n"
            + order_record_text(o)
        )
    raise ValueError(cmd.action)


def _paper_value(ledger_path) -> float | None:
    """Paper account value at the last closes (None if it cannot be priced)."""

    from core.reports.daily import value_holdings

    try:
        entries = load_ledger(ledger_path)
        holdings, invested = value_holdings(entries, "paper")
        if any(h.price_day is None for h in holdings):
            return None
        return cash_balance(entries, "paper") + invested
    except Exception:  # noqa: BLE001 - only used for a share shown to the user
        return None


def order_record_text(o) -> str:
    """What was recorded with the order (data, size, risk, reason)."""

    lines = ["🗂 Kayda geçen:"]
    if o.data_date:
        lines.append(f"  Veri: {o.data_date:%d.%m.%Y} kapanışı {tr(o.ref_close, 2)} TL")
    else:
        lines.append("  Veri: fiyat bulunamadı (alanlar boş kaydedildi)")
    if o.est_value is not None:
        share = f", sanal hesabın %{o.account_share * 100:.1f}'i" if o.account_share is not None else ""
        lines.append(f"  Tutar: ~{tr(o.est_value)} TL{share}")
    if o.atr_pct is not None:
        lines.append(f"  Oynaklık: günlük ortalama aralık (ATR) fiyatın %{o.atr_pct * 100:.1f}'i")
    if o.view:
        lines.append(f"  Teknik görünüm: {o.view} (skor {o.score:.0f}; getiri tahmin gücü kanıtlanmadı)")
    lines.append(f"  Gerekçe: {o.reason or '(yazılmadı)'}")
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
