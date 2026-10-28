"""
QuantBIST
Handler Registry
"""

from __future__ import annotations

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    filters,
)

from bot.analysis import analyze, levels_cmd, market_cmd, top
from bot.portfolio import alerts, paper, portfolio, report, trade
from bot.reports import (
    delete_screen,
    list_screens,
    performance,
    price_alarm,
    resend,
    save_screen,
    screen_button,
    screen_cmd,
    screen_explain,
    screen_fields,
    screen_more,
    screen_subscriptions,
    screen_templates,
    screen_virtual,
    status,
    stress_test,
    subscribe_screen,
    summary,
    unsubscribe_screen,
    yearly,
)
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
    ("seviye", levels_cmd),
    ("piyasa", market_cmd),
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
    ("rapor_tekrar", resend),
    ("yil", yearly),
    ("stres", stress_test),
    ("alarm", price_alarm),
    ("tara", screen_cmd),
    ("tara_kaydet", save_screen),
    ("tara_liste", list_screens),
    ("tara_sil", delete_screen),
    ("tara_abone", subscribe_screen),
    ("tara_abonelikler", screen_subscriptions),
    ("tara_abone_iptal", unsubscribe_screen),
    ("tara_sanal", screen_virtual),
    ("tara_alanlar", screen_fields),
    ("tara_aciklama", screen_explain),
    ("tara_devam", screen_more),
    ("tara_sablonlar", screen_templates),
)

# Telegram's "Menu" list (set when the bot starts); /help is the same as /start
MENU = (
    ("start", "komutlar ve düğmeler"),
    ("durum", "sistem sağlığı ve hedefler"),
    ("summary", "portföy ve piyasa özeti"),
    ("portfolio", "pozisyonlar ve kâr/zarar"),
    ("alerts", "açık risk uyarıları"),
    ("performans", "canlı ölçüm ve sanal hesap"),
    ("rapor_tekrar", "kayıtlı günlük raporu yeniden gönder"),
    ("report", "günlük raporu şimdi üret"),
    ("yil", "yıllık döküm: satışlar, temettü, komisyon"),
    ("stres", "pozisyonlar en kötü geçmiş düşüşlerde ne kaybederdi"),
    ("alarm", "kapanış alarmı: /alarm THYAO altında 240"),
    ("tara", "göstergeyle filtre: /tara rsi<30 ema20>ema50"),
    ("tara_kaydet", "taramayı kaydet: /tara_kaydet AD koşullar"),
    ("tara_liste", "kayıtlı taramalar"),
    ("tara_sil", "kayıtlı taramayı sil: /tara_sil AD"),
    ("tara_abone", "her akşam yalnız değişiklikleri gönder: /tara_abone AD"),
    ("tara_abonelikler", "tarama abonelikleri"),
    ("tara_abone_iptal", "aboneliği bitir: /tara_abone_iptal AD"),
    ("tara_sanal", "taramayı ölçüm amaçlı sanal kitapta işlet (varsayılan kapalı)"),
    ("tara_alanlar", "tarama alanları ve birimleri"),
    ("tara_aciklama", "bir hissede koşulların değeri: /tara_aciklama THYAO rsi<30"),
    ("tara_devam", "son taramanın sonraki 15 satırı"),
    ("tara_sablonlar", "hazır tarama şablonları (TradingView taramalarından)"),
    ("top", "teknik görünümü en güçlü hisseler"),
    ("analyze", "tek hisse: /analyze THYAO"),
    ("seviye", "destek/direnç seviyeleri: /seviye THYAO (öneri değil)"),
    ("piyasa", "piyasa rejimi, genişlik, sektörler (etiket, sinyal değil)"),
    ("watchlist", "takip listesi"),
    ("watchadd", "listeye ekle: /watchadd EREGL"),
    ("watchremove", "listeden çıkar"),
    ("watchscan", "takip listesini tara"),
    ("trade", "gerçekleşmiş işlemi deftere yaz"),
    ("paper", "sanal emir"),
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

    # the /tara buttons; the chat is checked inside (a callback has no message filter)
    app.add_handler(CallbackQueryHandler(screen_button, pattern=r"^tara:"))

    app.add_error_handler(on_error)
