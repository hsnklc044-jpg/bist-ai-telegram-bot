"""
QuantBIST
Shared helpers for Telegram handlers.
"""

from __future__ import annotations

from telegram import Update

TELEGRAM_LIMIT = 4096


def split_message(
    text: str,
    limit: int = TELEGRAM_LIMIT,
) -> list[str]:
    """
    Split long text on line boundaries so each part fits
    into a single Telegram message (same rule as the daily report).
    """

    from core.reports.daily import split_text

    return split_text(text, limit) or [text]


async def reply(
    update: Update,
    text: str,
) -> None:
    """Reply with text, splitting it if needed."""

    for part in split_message(text):
        await update.effective_message.reply_text(part)
