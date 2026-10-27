"""
QuantBIST
Report Commands
"""

from __future__ import annotations

import asyncio

from telegram import Update
from telegram.ext import ContextTypes

from bot.common import reply
from core.reports.forward import forward_report
from core.reports.health import health_report
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


async def performance(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /performans (live results of recorded views and the paper account)."""

    await reply(update, "⏳ Kayıtlar puanlanıyor...")

    text = await asyncio.to_thread(forward_report)

    await reply(update, text)


async def resend(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /rapor_tekrar [27.10]: send a saved daily report again (nothing is recomputed)."""

    from core.reports.daily import saved_report

    await reply(update, saved_report(" ".join(context.args or []) or None))


async def status(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /durum (system health from the records on disk)."""

    await reply(update, await asyncio.to_thread(health_report))
