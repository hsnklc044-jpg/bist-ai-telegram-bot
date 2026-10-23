"""
QuantBIST RC5
Watchlist Intelligence Service
"""

from __future__ import annotations

import re

from core.analytics.analyzer import (
    analyze_stock,
)
from core.infrastructure.logger import (
    get_logger,
)
from core.infrastructure.settings import settings
from core.watchlist.repository import (
    load_watchlist,
    save_watchlist,
)

logger = get_logger(__name__)



# =====================================================
# CONFIG
# =====================================================

MAX_WATCHLIST_SIZE = 30

_SYMBOL_PATTERN = re.compile(r"^[A-Z0-9]{2,10}$")


def _default_user_id() -> str:
    return str(settings.chat_id)


def normalize_symbol(
    symbol: str,
) -> str:
    """
    Convert user input into a Yahoo Finance BIST ticker.

    "eregl" -> "EREGL.IS", "THYAO.IS" -> "THYAO.IS"
    """

    code = (
        str(symbol)
        .strip()
        .upper()
        .removesuffix(".IS")
    )

    if not _SYMBOL_PATTERN.match(code):
        raise ValueError(
            f"Geçersiz hisse kodu: {symbol!r}"
        )

    return f"{code}.IS"


def add_symbol(
    user_id: str | int,
    symbol: str,
) -> str:
    """
    Add a symbol to the user's watchlist.

    Returns the normalized symbol. Adding an existing
    symbol is a no-op.
    """

    ticker = normalize_symbol(symbol)

    data = load_watchlist()
    symbols = data.setdefault(str(user_id), [])

    if ticker not in symbols:
        if len(symbols) >= MAX_WATCHLIST_SIZE:
            raise ValueError(
                f"Watchlist en fazla {MAX_WATCHLIST_SIZE} hisse alabilir."
            )

        symbols.append(ticker)
        save_watchlist(data)

    return ticker


def remove_symbol(
    user_id: str | int,
    symbol: str,
) -> bool:
    """
    Remove a symbol from the user's watchlist.

    Returns True when the symbol was present.
    """

    ticker = normalize_symbol(symbol)

    data = load_watchlist()
    symbols = data.get(str(user_id), [])

    if ticker not in symbols:
        return False

    symbols.remove(ticker)
    save_watchlist(data)

    return True





# =====================================================
# WATCHLIST SYMBOLS
# =====================================================


def get_watchlist(
    user_id: str | int | None = None,
) -> list[str]:
    """
    Return user watchlist symbols.
    """


    try:

        if user_id is None:
            user_id = _default_user_id()

        data = load_watchlist()


        if not data:

            return []



        return data.get(

            str(user_id),

            [],

        )


    except Exception as exc:


        logger.exception(

            "Watchlist loading failed | %s",

            exc,

        )


        return []





# =====================================================
# WATCHLIST ANALYSIS
# =====================================================


def get_watchlist_details(
    user_id: str | int | None = None,
) -> list[dict]:
    """
    Analyze watchlist symbols.

    Returns RC5 dashboard ready data.
    """


    symbols = get_watchlist(
        user_id,
    )


    results: list[dict] = []



    for symbol in symbols:


        try:


            analysis = analyze_stock(
                symbol,
            )


            if not analysis:

                continue



            results.append(

                {


                    "symbol":

                        analysis.get(
                            "symbol",
                            symbol,
                        ),



                    "price":

                        analysis.get(
                            "price",
                            0,
                        ),



                    "signal":

                        analysis.get(
                            "signal",
                            "WATCH",
                        ),



                    "score":

                        analysis.get(
                            "score",
                            0,
                        ),



                    "confidence":

                        analysis.get(
                            "confidence",
                            0,
                        ),



                    "trend":

                        analysis.get(
                            "trend",
                            "NEUTRAL",
                        ),



                    "momentum":

                        analysis.get(
                            "momentum",
                            "NEUTRAL",
                        ),



                    "risk_level":

                        analysis.get(
                            "risk_level",
                            "LOW",
                        ),



                    "entry_price":

                        analysis.get(
                            "entry_price",
                            0,
                        ),



                    "stop_loss":

                        analysis.get(
                            "stop_loss",
                            0,
                        ),



                    "target_1":

                        analysis.get(
                            "target_1",
                            0,
                        ),


                }

            )



        except Exception as exc:


            logger.warning(

                "Watchlist analysis failed | %s | %s",

                symbol,

                exc,

            )


            continue



    results.sort(

        key=lambda item:

        item.get(
            "score",
            0,
        ),

        reverse=True,

    )



    return results





# =====================================================
# EXPORTS
# =====================================================


__all__ = [

    "normalize_symbol",

    "add_symbol",

    "remove_symbol",

    "get_watchlist",

    "get_watchlist_details",

]
