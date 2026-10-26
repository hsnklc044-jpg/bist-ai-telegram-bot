"""
QuantBIST RC4
Watchlist Scanner
"""

from __future__ import annotations

from core.analytics.analyzer import analyze_stock
from core.config.thresholds import SIGNAL_VIEW_LABELS
from core.signals_log import log_analysis
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

        view = SIGNAL_VIEW_LABELS.get(result["signal"], result["signal"])
        log_analysis("watchscan", result, view)  # same record as /top and /analyze

        report += (
            f"📈 {symbol}\n"
            f"📊 Görünüm : {view} (skor {result['score']})\n"
            f"📊 Trend : {result['trend']}\n\n"
        )

    return report
