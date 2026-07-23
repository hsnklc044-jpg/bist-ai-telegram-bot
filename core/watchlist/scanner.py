"""
QuantBIST RC4
Watchlist Scanner
"""

from __future__ import annotations

from core.analytics.analyzer import analyze_stock
from core.watchlist.service import get_watchlist


def generate_watchlist_scan(chat_id: int) -> str:

    symbols = get_watchlist(chat_id)

    if not symbols:
        return "📌 Watchlist boş."

    report = "📌 WATCHLIST SCAN\n\n"

    for symbol in symbols:

        result = analyze_stock(symbol)

        if result is None:
            continue

        report += (
            f"📈 {symbol}\n"
            f"⭐ Score : {result['score']}\n"
            f"🎯 Signal : {result['signal']}\n"
            f"📊 Trend : {result['trend']}\n\n"
        )

    return report
