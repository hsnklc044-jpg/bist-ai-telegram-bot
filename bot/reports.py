"""
QuantBIST
Report Commands
"""

from __future__ import annotations

import asyncio

from telegram import Update
from telegram.ext import ContextTypes

from bot.common import reply
from core.dashboard.service import get_dashboard
from core.infrastructure.exceptions import DashboardError
from core.reports import generate_summary_report

NO_DATA_MESSAGE = (
    "⚠️ Özet hazırlanamadı: fiyat verisi yok.\n"
    "Sunucuda python -m core.market.update çalıştırıp tekrar deneyin."
)


def _build_summary() -> str:
    return generate_summary_report(get_dashboard())


async def summary(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /summary."""

    await reply(update, "⏳ Özet hazırlanıyor...")

    try:
        text = await asyncio.to_thread(_build_summary)
    except DashboardError:
        text = NO_DATA_MESSAGE

    await reply(update, text)
