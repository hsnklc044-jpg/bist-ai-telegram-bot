"""
QuantBIST RC4
Watchlist Commands
"""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from core.watchlist.service import (
    add_symbol,
    remove_symbol,
    get_watchlist,
)

from core.watchlist.scanner import (
    generate_watchlist_scan,
)


async def watchadd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not context.args:

        await update.message.reply_text(
            "Kullanım:\n/watchadd EREGL"
        )
        return

    symbol = context.args[0]

    add_symbol(
        update.effective_chat.id,
        symbol,
    )

    await update.message.reply_text(
        f"✅ {symbol.upper().replace('.IS','')}.IS watchlist'e eklendi."
    )


async def watchremove(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not context.args:

        await update.message.reply_text(
            "Kullanım:\n/watchremove EREGL"
        )
        return

    symbol = context.args[0]

    remove_symbol(
        update.effective_chat.id,
        symbol,
    )

    await update.message.reply_text(
        f"❌ {symbol.upper().replace('.IS','')}.IS watchlist'ten kaldırıldı."
    )


async def watchlist(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    symbols = get_watchlist(
        update.effective_chat.id
    )

    if not symbols:

        await update.message.reply_text(
            "📌 Watchlist boş."
        )
        return

    message = "📌 WATCHLIST\n\n"

    for symbol in symbols:

        message += f"• {symbol}\n"

    await update.message.reply_text(message)


async def watchscan(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    report = generate_watchlist_scan(
        update.effective_chat.id
    )

    await update.message.reply_text(report)