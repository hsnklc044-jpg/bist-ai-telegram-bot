"""
QuantBIST RC4
Watchlist Scanner
"""

from __future__ import annotations

from core.analytics.analyzer import analyze_stock
from core.analytics.scoring import describe_signal
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
            f"⭐ Skor : {result['score']}\n"
            f"🎯 Görünüm : {describe_signal(result['signal'])}\n"
            f"📊 Trend : {result['trend']}\n\n"
        )

    return report
