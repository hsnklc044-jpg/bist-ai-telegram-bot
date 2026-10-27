"""
QuantBIST
Handler Registry
"""

from __future__ import annotations

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    filters,
)

from bot.analysis import analyze, top
from bot.portfolio import alerts, paper, portfolio, report, trade
from bot.reports import performance, status, summary
from bot.start import start
from bot.watchlist import (
    watchadd,
    watchlist,
    watchremove,
    watchscan,
)
from core.infrastructure.exceptions import PersonalFileError
from core.infrastructure.logger import get_logger

logger = get_logger(__name__)
_conflict_reported = False  # a second bot with the same token is reported once per run

COMMANDS = (
    ("start", start),
    ("help", start),
    ("summary", summary),
    ("top", top),
    ("analyze", analyze),
    ("watchadd", watchadd),
    ("watchremove", watchremove),
    ("watchlist", watchlist),
    ("watchscan", watchscan),
    ("portfolio", portfolio),
    ("trade", trade),
    ("paper", paper),
    ("alerts", alerts),
    ("report", report),
    ("performans", performance),
    ("durum", status),
)


async def on_error(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Log the failure and tell the user something went wrong."""

    from telegram.error import Conflict

    if isinstance(context.error, Conflict):
        # another process polls with the same token; Telegram repeats this every few seconds
        global _conflict_reported
        if not _conflict_reported:
            _conflict_reported = True
            logger.error(
                "Bu token ile aynı anda iki bot çalışıyor; Telegram ikincisini reddediyor. "
                "Yalnız biri açık kalsın: elle açılan 'python main.py' penceresini kapatın, "
                "botu 'QuantBIST Bot' görevi başlatsın."
            )
        return

    logger.error(
        "Telegram handler failed.",
        exc_info=context.error,
    )

    if isinstance(update, Update) and update.effective_message:
        if isinstance(context.error, PersonalFileError):
            # a damaged personal file: say which one and what to do
            await update.effective_message.reply_text(f"⚠️ {context.error}")
            return
        if isinstance(context.error, PermissionError):
            # Windows: the file is open in another program (e.g. Excel); nothing was written
            from pathlib import Path

            name = Path(context.error.filename or "dosya").name
            await update.effective_message.reply_text(
                f"⚠️ {name} kilitli: Excel gibi bir programda açık olabilir. İşlem kaydedilmedi; "
                "dosyayı kapatıp komutu yeniden gönderin."
            )
            return
        await update.effective_message.reply_text(
            "⚠️ Bir hata oluştu, ayrıntılar log dosyasında."
        )


def register_handlers(
    app: Application,
    chat_id: int,
) -> None:
    """
    Register Telegram handlers.

    Only messages from `chat_id` are answered; everyone
    else is ignored.
    """

    allowed = filters.Chat(chat_id=chat_id)

    for command, callback in COMMANDS:
        app.add_handler(
            CommandHandler(
                command,
                callback,
                filters=allowed,
            )
        )

    app.add_error_handler(on_error)
