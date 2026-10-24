"""
QuantBIST
Backtest Command
"""

from __future__ import annotations

import asyncio

from telegram import Update
from telegram.ext import ContextTypes

from bot.common import reply
from core.backtest.runner import (
    DISCLAIMER,
    PERIOD,
    format_portfolio,
    format_symbol,
    run_symbol,
    run_universe,
)
from core.infrastructure.exceptions import MarketError
from core.market.data import load_price_history
from core.market.quality import suspicious_jumps
from core.watchlist.service import normalize_symbol

NO_DATA = "⚠️ Backtest için fiyat verisi yok. Sunucuda python -m core.market.update çalıştırın."


def _single(symbol: str) -> str:
    result = run_symbol(symbol)
    text = format_symbol(result)

    jumps = suspicious_jumps(load_price_history(symbol, period=PERIOD))
    if not jumps.empty:
        days = ", ".join(f"{d.date()} {r:+.0%}" for d, r in jumps.items())
        text += f"\n\n⚠️ Veride düzeltilmemiş sıçrama var ({days}); sonuç güvenilir değil."

    return f"{text}\n\n⚠️ {DISCLAIMER}"


def _universe() -> str:
    return format_portfolio(run_universe())


async def backtest(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /backtest and /backtest SYMBOL."""

    if len(context.args) > 1:
        await reply(update, "Kullanım:\n/backtest\n/backtest THYAO")
        return

    if context.args:
        try:
            symbol = normalize_symbol(context.args[0])
        except ValueError as exc:
            await reply(update, str(exc))
            return

        job, args = _single, (symbol,)
    else:
        job, args = _universe, ()

    await reply(update, "⏳ Backtest çalışıyor...")

    try:
        text = await asyncio.to_thread(job, *args)
    except (MarketError, ValueError):
        text = NO_DATA

    await reply(update, text)
