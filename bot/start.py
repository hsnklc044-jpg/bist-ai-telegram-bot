"""
QuantBIST RC4
Start Command
"""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /start command."""

    message = (
        "🚀 QuantBIST RC4\n\n"
        "Sistem başarıyla başlatıldı.\n\n"
        "Kullanılabilir komutlar:\n"
        "/start\n"
        "/summary\n"
        "/portfolio\n"
        "/analyze"
    )

    await update.message.reply_text(message)