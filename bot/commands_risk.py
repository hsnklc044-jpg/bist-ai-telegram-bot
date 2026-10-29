"""
QuantBIST
/risk: the risk budget (Talimat E, DECISIONS K-56). Measures and limits only; never advice.
"""

from __future__ import annotations

import asyncio

from telegram import Update
from telegram.ext import ContextTypes

from bot.common import reply


async def risk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /risk, /risk ekle THYAO 100 and /risk denge (each with gercek|sanal)."""

    from core.alerts import budget

    await reply(update, await asyncio.to_thread(budget.command_text, list(context.args or [])))
