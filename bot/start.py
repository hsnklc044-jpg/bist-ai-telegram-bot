"""
QuantBIST
Start / Help Command
"""

from __future__ import annotations

from telegram import KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes

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
/durum – sistem sağlığı: son rapor, veri, canlı kayıt, yedek
/rapor_tekrar – kayıtlı son raporu yeniden gönder (/rapor_tekrar 27.10)
/yil – yıllık döküm: satış sonuçları, temettü, komisyon (/yil 2026 sanal)
/help – bu mesaj

ℹ️ Teknik skorun backtest'te getiri tahmin gücü bulunmadı;
bilgi amaçlıdır, yatırım tavsiyesi değildir. Bot gerçek emir göndermez."""


# everyday commands as buttons under the text field (a tap sends the command)
KEYBOARD = ReplyKeyboardMarkup(
    [[KeyboardButton(c) for c in row] for row in (
        ("/durum", "/summary", "/portfolio"),
        ("/alerts", "/performans", "/rapor_tekrar"),
    )],
    resize_keyboard=True,
    is_persistent=True,
)


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /start and /help."""

    await update.effective_message.reply_text(HELP_TEXT, reply_markup=KEYBOARD)
