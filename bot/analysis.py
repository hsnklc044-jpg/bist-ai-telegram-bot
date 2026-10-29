"""
QuantBIST
Analysis Commands

The technical score is shown as a "view", not as a buy/sell call:
the v0.10.0 backtest found no predictive power in it (see
core/backtest/run.py). Wording changes when a strategy passes the
backtest.
"""

from __future__ import annotations

import asyncio

from telegram import Update
from telegram.ext import ContextTypes

from bot.common import reply
from core.analytics.analyzer import analyze_stock
from core.analytics.signals import get_top_signals
from core.config.thresholds import SIGNAL_VIEW_LABELS
from core.signals_log import log_analysis
from core.watchlist.service import normalize_symbol

VIEW_LABELS = SIGNAL_VIEW_LABELS

POSITIVE = ("STRONG BUY", "BUY")

DISCLAIMER = (
    "ℹ️ Bu teknik skorun 2022–2026 backtest'inde getiri tahmin gücü "
    "bulunmadı. Bilgi amaçlıdır, yatırım tavsiyesi değildir."
)


def view_label(signal: str) -> str:
    return VIEW_LABELS.get(signal, signal)


def _format_signals(signals: list[dict]) -> str:
    lines = ["📈 Teknik görünümü en güçlü hisseler", ""]

    for item in signals[:10]:
        lines += [
            f"🏷 {item['symbol']}",
            f"📊 Görünüm : {view_label(item['signal'])} (skor {item['score']})",
            f"📈 Trend : {item['trend']}",
            "",
        ]

    lines.append(DISCLAIMER)

    return "\n".join(lines)


def _levels(result: dict) -> str:
    if result["signal"] not in POSITIVE:
        return "📍 Seviye gösterilmiyor (görünüm pozitif değil)"

    return f"""📍 ATR seviyeleri (bilgi amaçlı)
🛑 2 ATR altı : {result["stop_loss"]}
⬆️ 2 ATR üstü : {result["target_1"]}
⬆️ 4 ATR üstü : {result["target_2"]}"""


def _format_analysis(result: dict, levels: str = "") -> str:
    return f"""📊 {result["symbol"]}

💰 Fiyat : {result["price"]}

📊 Görünüm : {view_label(result["signal"])} (skor {result["score"]})
📈 Trend : {result["trend"]}

⚡ RSI : {result["rsi"]:.1f}
📉 MACD : {result["macd"]:.2f}

📦 Hacim oranı : {result["volume_ratio"]}
🌊 Volatilite (ATR/fiyat) : %{result["volatility"] * 100:.2f}

{_levels(result)}
{chr(10) + levels + chr(10) if levels else ""}
📈 EMA20 : {result["ma20"]:.2f}
📈 EMA50 : {result["ma50"]:.2f}

{DISCLAIMER}"""


async def top(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /top."""

    await reply(update, "⏳ Hisseler taranıyor...")

    signals = await asyncio.to_thread(get_top_signals)

    if not signals:
        await reply(update, "Teknik görünümü pozitif hisse bulunamadı.")
        return

    for item in signals[:10]:
        await asyncio.to_thread(log_analysis, "top", item, view_label(item["signal"]))

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

    await asyncio.to_thread(log_analysis, "analyze", result, view_label(result["signal"]))

    await reply(update, _format_analysis(result, await asyncio.to_thread(_level_block, symbol, 3)))


def _level_block(symbol: str, k: int | None) -> str:
    """Support and resistance (K-49); a failure only costs this block."""

    from core.analytics.levels import levels_text
    from core.reports.daily import adjusted_bars

    try:
        return levels_text(symbol, adjusted_bars(symbol), k=k)
    except Exception:  # noqa: BLE001
        return ""


async def fundamentals_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /temel SYMBOL: the K-57 fundamental scores, or "veri yok"."""

    from core.fundamentals import scores

    await reply(update, await asyncio.to_thread(scores.command_text, list(context.args or [])))


async def scenario_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /senaryo: scenario templates or the user's own levels (K-55; a calculator, not advice)."""

    from core.analytics import scenarios

    await reply(update, await asyncio.to_thread(scenarios.command_text, list(context.args or [])))


async def market_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /piyasa: the regime label, breadth and the main sectors against XU100 (K-51)."""

    from core.market import regime

    await reply(update, await asyncio.to_thread(regime.live_text))


async def levels_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /seviye SYMBOL: every support and resistance level (teknik seviye, öneri değil)."""

    if len(context.args or []) != 1:
        await reply(update, "Kullanım:\n/seviye THYAO")
        return
    try:
        symbol = normalize_symbol(context.args[0])
    except ValueError as exc:
        await reply(update, str(exc))
        return
    text = await asyncio.to_thread(_level_block, symbol, None)
    await reply(update, text or f"{symbol} için seviye hesaplanamadı.")
