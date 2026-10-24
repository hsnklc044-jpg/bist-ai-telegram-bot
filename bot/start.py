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
/rotasyon – momentum rotasyonu: bu ayın 5 hissesi
/top – teknik skoru en yüksek hisseler
/analyze THYAO – tek hisse teknik özeti
/backtest – teknik skorun 5 yıllık geçmiş testi
/backtest THYAO – tek hisse için geçmiş test
/summary – portföy ve piyasa özeti
/watchlist – takip listesi
/watchadd EREGL – listeye ekle
/watchremove EREGL – listeden çıkar
/watchscan – takip listesini tara
/help – bu mesaj

Her ayın ilk seansından sonra (18:45) rotasyon değişiklikleri otomatik bildirilir.

⚠️ Geçmiş performans geleceği garanti etmez; yatırım tavsiyesi değildir."""


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /start and /help."""

    await reply(update, HELP_TEXT)
