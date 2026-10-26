"""
QuantBIST
Report Commands
"""

from __future__ import annotations

import asyncio

from telegram import Update
from telegram.ext import ContextTypes

from bot.common import reply
from core.reports.overview import build_overview


def _build_summary() -> str:
    return build_overview().text


async def summary(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /summary (read-only: stored prices and personal records)."""

    await reply(update, "⏳ Özet hazırlanıyor...")

    text = await asyncio.to_thread(_build_summary)

    await reply(update, text)
