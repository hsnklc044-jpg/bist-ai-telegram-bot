"""
QuantBIST
Rotation Command and Monthly Notice
"""

from __future__ import annotations

import asyncio

from telegram import Update
from telegram.ext import ContextTypes

from bot.common import reply
from core.infrastructure.exceptions import MarketError
from core.infrastructure.logger import get_logger
from core.rotation.service import build_report, check_rebalance, format_report

logger = get_logger(__name__)

NO_DATA = "⚠️ Rotasyon için fiyat verisi yok. Sunucuda python -m core.market.update çalıştırın."


def _report() -> str:
    return format_report(build_report())


async def rotation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /rotasyon."""

    await reply(update, "⏳ Hisseler sıralanıyor...")

    try:
        text = await asyncio.to_thread(_report)
    except (MarketError, ValueError):
        text = NO_DATA

    await reply(update, text)


async def rebalance_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Daily after the close: send the monthly rebalance notice when due."""

    try:
        message = await asyncio.to_thread(check_rebalance)
    except Exception:  # noqa: BLE001
        logger.exception("Rebalance check failed.")
        return

    if message:
        await context.bot.send_message(chat_id=context.job.chat_id, text=message)
