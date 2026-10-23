"""
QuantBIST
Start / Help Command
"""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from bot.common import reply
from core.infrastructure.settings import settings

HELP_TEXT = f"""🚀 {settings.app_name} v{settings.version}

Komutlar:
/top – en güçlü sinyaller
/analyze THYAO – tek hisse analizi
/summary – portföy ve piyasa özeti
/watchlist – takip listesi
/watchadd EREGL – listeye ekle
/watchremove EREGL – listeden çıkar
/watchscan – takip listesini tara
/help – bu mesaj

⚠️ Sinyaller henüz backtest edilmedi; yatırım tavsiyesi değildir."""


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /start and /help."""

    await reply(update, HELP_TEXT)
