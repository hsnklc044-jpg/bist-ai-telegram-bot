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
/top – teknik görünümü en güçlü hisseler
/analyze THYAO – tek hisse teknik analizi
/summary – portföy ve piyasa özeti
/watchlist – takip listesi
/watchadd EREGL – listeye ekle
/watchremove EREGL – listeden çıkar
/watchscan – takip listesini tara

Portföy ve risk:
/portfolio – pozisyonlar ve kâr/zarar (gerçek ve sanal)
/trade al THYAO 100 285,50 – gerçekleşmiş işlemi deftere yaz
/paper al THYAO 100 – sanal emir (bir sonraki açılıştan dolar)
/paper – bekleyen sanal emirler, /paper iptal 3
/alerts – açık risk uyarıları
/report – günlük raporu şimdi üret
/performans – kayıtlı görünümlerin ve sanal hesabın canlı sonucu (XU100'e karşı)
/help – bu mesaj

ℹ️ Teknik skorun backtest'te getiri tahmin gücü bulunmadı;
bilgi amaçlıdır, yatırım tavsiyesi değildir. Bot gerçek emir göndermez."""


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /start and /help."""

    await reply(update, HELP_TEXT)
