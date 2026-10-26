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
from core.reports import generate_summary_report


def _build_summary() -> str:
    return generate_summary_report(get_dashboard())


async def summary(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /summary."""

    await reply(update, "⏳ Özet hazırlanıyor...")

    text = await asyncio.to_thread(_build_summary)

    await reply(update, text)
