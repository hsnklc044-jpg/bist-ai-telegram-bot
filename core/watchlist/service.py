"""
QuantBIST RC4
Watchlist Service
"""

from __future__ import annotations

from core.analytics.analyzer import analyze_stock
from core.watchlist.repository import load_watchlist

DEFAULT_USER_ID = "1790584407"


def get_watchlist(user_id: str | int = DEFAULT_USER_ID) -> list[str]:
    """
    Kullanıcının watchlist sembollerini döndürür.
    """

    data = load_watchlist()

    if not data:
        return []

    return data.get(str(user_id), [])


def get_watchlist_details(
    user_id: str | int = DEFAULT_USER_ID,
) -> list[dict]:
    """
    Watchlist hisselerini analiz ederek
    Dashboard'a hazır hale getirir.
    """

    symbols = get_watchlist(user_id)

    results = []

    for symbol in symbols:

        try:

            analysis = analyze_stock(symbol)

            if analysis:

                results.append({

                    "symbol": analysis["symbol"],

                    "signal": analysis["signal"],

                    "score": analysis["score"],

                    "trend": analysis["trend"],

                })

        except Exception:

            continue

    return results