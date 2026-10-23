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
    into a single Telegram message.
    """

    if len(text) <= limit:
        return [text]

    parts: list[str] = []
    current = ""

    for line in text.splitlines(keepends=True):
        while len(line) > limit:
            if current:
                parts.append(current)
                current = ""
            parts.append(line[:limit])
            line = line[limit:]

        if len(current) + len(line) > limit:
            parts.append(current)
            current = ""

        current += line

    if current:
        parts.append(current)

    return parts


async def reply(
    update: Update,
    text: str,
) -> None:
    """Reply with text, splitting it if needed."""

    for part in split_message(text):
        await update.effective_message.reply_text(part)
