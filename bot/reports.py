"""
QuantBIST RC4
Report Commands
"""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from core.reports import generate_summary_report


async def summary(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /summary command."""

    await update.message.reply_text(
        generate_summary_report()
    )