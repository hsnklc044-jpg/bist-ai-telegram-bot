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
from core.analytics.scoring import describe_signal
from core.analytics.signals import get_top_signals
from core.watchlist.service import normalize_symbol

NOTE = (
    "ℹ️ Teknik skor tek başına backtestte al-tutu geçemedi; al-sat sinyali değildir.\n"
    "Test edilmiş strateji için: /rotasyon"
)


def _format_signals(signals: list[dict]) -> str:
    lines = ["📈 TEKNİK SKORU EN YÜKSEK HİSSELER", ""]

    for item in signals[:10]:
        lines += [
            f"🏷 {item['symbol']}",
            f"🎯 Görünüm : {describe_signal(item['signal'])}",
            f"📊 Skor : {item['score']}",
            f"📈 Trend : {item['trend']}",
            "",
        ]

    lines.append(NOTE)

    return "\n".join(lines)


POSITIVE = ("STRONG BUY", "BUY")


def _trade_levels(result: dict) -> str:
    if result["signal"] not in POSITIVE:
        return "📐 ATR seviyesi yok (görünüm pozitif değil)"

    return f"""📐 ATR seviyeleri (bilgi amaçlı):
📍 Fiyat : {result["entry_price"]}
🛑 Stop : {result["stop_loss"]}

🎯 Hedef 1 : {result["target_1"]}
🎯 Hedef 2 : {result["target_2"]}"""


def _format_analysis(result: dict) -> str:
    return f"""📊 {result["symbol"]}

💰 Fiyat : {result["price"]}

🎯 Teknik görünüm : {describe_signal(result["signal"])}
📈 Skor : {result["score"]}
📊 Trend : {result["trend"]}

⚡ RSI : {result["rsi"]:.1f}
📉 MACD : {result["macd"]:.2f}

📦 Hacim oranı : {result["volume_ratio"]}
🌊 Volatilite (ATR/fiyat) : %{result["volatility"] * 100:.2f}

{_trade_levels(result)}

📈 EMA20 : {result["ma20"]:.2f}
📈 EMA50 : {result["ma50"]:.2f}

{NOTE}"""


async def top(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /top."""

    await reply(update, "⏳ Hisseler taranıyor...")

    signals = await asyncio.to_thread(get_top_signals)

    if not signals:
        await reply(update, "Skoru yeterli hisse bulunamadı.")
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
