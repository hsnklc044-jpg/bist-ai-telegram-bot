"""
QuantBIST
Portfolio, ledger, paper orders, alerts and the daily report in Telegram.
"""

from __future__ import annotations

import asyncio

from telegram import Update
from telegram.ext import ContextTypes

from bot.common import reply
from core.ledger.book import LedgerError
from core.ledger.commands import parse_paper, parse_trade
from core.ledger.service import alerts_text, paper_action, portfolio_text, record_trade


async def portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /portfolio."""

    try:
        text = await asyncio.to_thread(portfolio_text)
    except LedgerError as exc:
        text = f"Defter okunamadı: {exc}"
    await reply(update, text)


async def trade(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /trade (record a real, already executed trade)."""

    try:
        text = await asyncio.to_thread(record_trade, parse_trade(context.args))
    except (LedgerError, ValueError) as exc:
        text = f"❌ {exc}"
    await reply(update, text)


async def paper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /paper (simulated orders; nothing is sent to a broker)."""

    try:
        text = await asyncio.to_thread(paper_action, parse_paper(context.args))
    except (LedgerError, ValueError) as exc:
        text = f"❌ {exc}"
    await reply(update, text)


async def alerts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /alerts."""

    await reply(update, await asyncio.to_thread(alerts_text))


def _daily_text() -> str:
    from core.market import store
    from core.market.universe import BENCHMARK, load_universe
    from core.reports.daily import build_daily
    from core.reports.runs import ReportBusy, report_lock

    try:
        with report_lock():
            store.update([BENCHMARK, *load_universe()])
            return build_daily().text
    except ReportBusy as exc:
        return f"⏳ {exc} Birkaç dakika sonra tekrar deneyin."


async def report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /report (same report as the scheduled one)."""

    await reply(update, "⏳ Fiyatlar güncelleniyor ve rapor hazırlanıyor...")
    try:
        text = await asyncio.to_thread(_daily_text)
    except LedgerError as exc:
        text = f"Defter okunamadı: {exc}"
    await reply(update, text)
