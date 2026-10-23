"""
QuantBIST
Analysis Commands
"""

from __future__ import annotations

import asyncio

from telegram import Update
from telegram.ext import ContextTypes

from bot.common import reply
from core.analytics.analyzer import analyze_stock
from core.analytics.signals import get_top_signals
from core.watchlist.service import normalize_symbol


def _format_signals(signals: list[dict]) -> str:
    lines = ["📈 QUANTBIST TOP SIGNALS", ""]

    for item in signals[:10]:
        lines += [
            f"🏷 {item['symbol']}",
            f"🎯 Signal : {item['signal']}",
            f"📊 Score : {item['score']}",
            f"📈 Trend : {item['trend']}",
            "",
        ]

    return "\n".join(lines)


BUY_SIGNALS = ("STRONG BUY", "BUY")


def _trade_levels(result: dict) -> str:
    if result["signal"] not in BUY_SIGNALS:
        return "📍 İşlem seviyesi yok (alım sinyali değil)"

    return f"""📍 Entry : {result["entry_price"]}
🛑 Stop Loss : {result["stop_loss"]}

🎯 Target 1 : {result["target_1"]}
🎯 Target 2 : {result["target_2"]}"""


def _format_analysis(result: dict) -> str:
    return f"""📊 {result["symbol"]}

💰 Price : {result["price"]}

🎯 Signal : {result["signal"]}
📈 Score : {result["score"]}
📊 Trend : {result["trend"]}

⚡ RSI : {result["rsi"]:.1f}
📉 MACD : {result["macd"]:.2f}

📦 Volume Ratio : {result["volume_ratio"]}
🌊 Volatility (ATR/fiyat) : %{result["volatility"] * 100:.2f}

🛡 Confidence : {result["confidence"]}%

{_trade_levels(result)}

📈 EMA20 : {result["ma20"]:.2f}
📈 EMA50 : {result["ma50"]:.2f}"""


async def top(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /top."""

    await reply(update, "⏳ Hisseler taranıyor...")

    signals = await asyncio.to_thread(get_top_signals)

    if not signals:
        await reply(update, "Uygun sinyal bulunamadı.")
        return

    await reply(update, _format_signals(signals))


async def analyze(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /analyze SYMBOL."""

    if len(context.args) != 1:
        await reply(update, "Kullanım:\n/analyze THYAO")
        return

    try:
        symbol = normalize_symbol(context.args[0])
    except ValueError as exc:
        await reply(update, str(exc))
        return

    result = await asyncio.to_thread(analyze_stock, symbol)

    if result is None:
        await reply(update, f"{symbol} için analiz yapılamadı.")
        return

    await reply(update, _format_analysis(result))
