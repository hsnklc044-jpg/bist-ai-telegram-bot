"""
QuantBIST
/panik and /devam: the emergency stop of the paper signal system (core.signals.panic).
"""

from __future__ import annotations

import asyncio

from telegram import Update
from telegram.ext import ContextTypes

from bot.common import reply


def panic_text() -> str:
    from core.market.calendar import now_istanbul
    from core.signals import panic

    if panic.active():
        return f"⛔ Panik kilidi zaten açık ({panic.since()}). Kaldırmak için /devam."
    cancelled = panic.trigger(now_istanbul().date())
    return ("⛔ PANİK: sistem kilitlendi.\n"
            f"• {cancelled} sanal sinyal kapandı: bekleyenler iptal edildi; açık pozisyonlar son kapanıştan "
            "kapatıldı ve sonucu kasaya yazıldı (fiyatı olmayan açık kalır).\n"
            "• Saatlik takip, günlük sinyal adımı, tarama abonelikleri ve /tara durduruldu.\n"
            "• Kilit dosyada tutulur: bot ya da bilgisayar yeniden başlasa da sürer.\n"
            "/durum çalışmaya devam eder. Kaldırmak için /devam.")


def resume_text() -> str:
    from core.signals import panic

    if not panic.release():
        return "Panik kilidi yok; sistem zaten çalışıyor."
    return "✅ Panik kilidi kaldırıldı: takip, taramalar ve /tara yeniden açık. İptal edilen sinyaller geri gelmez."


async def panic_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /panik: cancel the open paper signals and lock the system."""

    await reply(update, await asyncio.to_thread(panic_text))


async def resume_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /devam: lift the panic lock."""

    await reply(update, await asyncio.to_thread(resume_text))


async def otonom_stop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /otonom_dur: stop the autonomous development (no merge, install or delete; reports only)."""

    from core import otonom
    from core.market.calendar import now_istanbul

    await reply(update, await asyncio.to_thread(otonom.stop, now_istanbul()))


async def otonom_resume_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /otonom_devam: lift the user's stop flag and the automatic brake."""

    from core import otonom

    await reply(update, await asyncio.to_thread(otonom.resume))


__all__ = ["otonom_resume_cmd", "otonom_stop_cmd", "panic_cmd", "panic_text", "resume_cmd", "resume_text"]
