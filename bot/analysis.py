"""
QuantBIST RC4
Analysis Commands
"""

from telegram import Update
from telegram.ext import ContextTypes

from core.analytics.signals import get_top_signals
from core.analytics.analyzer import analyze_stock


async def top(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    signals = get_top_signals()

    if not signals:

        await update.message.reply_text(
            "Uygun sinyal bulunamadı."
        )

        return

    message = "📈 QUANTBIST TOP SIGNALS\n\n"

    for item in signals[:10]:

        message += (
            f"🏷 {item['symbol']}\n"
            f"🎯 Signal : {item['signal']}\n"
            f"📊 Score : {item['score']}\n"
            f"📈 Trend : {item['trend']}\n\n"
        )

    await update.message.reply_text(message)


async def analyze(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if len(context.args) != 1:

        await update.message.reply_text(
            "Kullanım:\n/analyze THYAO"
        )

        return

    symbol = context.args[0].upper()

    if not symbol.endswith(".IS"):
        symbol += ".IS"

    result = analyze_stock(symbol)

    if result is None:

        await update.message.reply_text(
            "Analiz yapılamadı."
        )

        return

    message = f"""
📊 {result["symbol"]}

💰 Price : {result["price"]}

🎯 Signal : {result["signal"]}
📈 Score : {result["score"]}
📊 Trend : {result["trend"]}

⚡ RSI : {result["rsi"]}
📉 MACD : {result["macd"]}

📦 Volume Ratio : {result["volume_ratio"]}
🌊 Volatility : {result["volatility"]}%

🛡 Confidence : {result["confidence"]}%

📍 Entry : {result["entry_price"]}
🛑 Stop Loss : {result["stop_loss"]}

🎯 Target 1 : {result["target_1"]}
🎯 Target 2 : {result["target_2"]}

📈 MA20 : {result["ma20"]}
📈 MA50 : {result["ma50"]}
"""

    await update.message.reply_text(message)