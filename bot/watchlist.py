"""
QuantBIST
Watchlist Commands
"""

from __future__ import annotations

import asyncio

from telegram import Update
from telegram.ext import ContextTypes

from bot.common import reply
from core.watchlist.scanner import generate_watchlist_scan
from core.watchlist.service import (
    add_symbol,
    get_watchlist,
    remove_symbol,
)


async def watchadd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /watchadd SYMBOL."""

    if not context.args:
        await reply(update, "Kullanım:\n/watchadd EREGL")
        return

    try:
        symbol = add_symbol(update.effective_chat.id, context.args[0])
    except ValueError as exc:
        await reply(update, str(exc))
        return

    await reply(update, f"✅ {symbol} watchlist'e eklendi.")


async def watchremove(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /watchremove SYMBOL."""

    if not context.args:
        await reply(update, "Kullanım:\n/watchremove EREGL")
        return

    try:
        removed = remove_symbol(update.effective_chat.id, context.args[0])
    except ValueError as exc:
        await reply(update, str(exc))
        return

    if removed:
        await reply(update, "❌ Watchlist'ten kaldırıldı.")
    else:
        await reply(update, "Bu hisse watchlist'te yok.")


async def watchlist(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /watchlist."""

    symbols = get_watchlist(update.effective_chat.id)

    if not symbols:
        await reply(update, "📌 Watchlist boş.")
        return

    lines = ["📌 WATCHLIST", ""] + [f"• {symbol}" for symbol in symbols]

    await reply(update, "\n".join(lines))


async def watchscan(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /watchscan."""

    await reply(update, "⏳ Watchlist taranıyor...")

    report = await asyncio.to_thread(
        generate_watchlist_scan,
        update.effective_chat.id,
    )

    await reply(update, report)
