"""
QuantBIST RC5
Watchlist Intelligence Service
"""

from __future__ import annotations

from core.infrastructure.logger import (
    get_logger,
)
from core.infrastructure.settings import settings
from core.market.symbols import normalize_symbol
from core.watchlist.repository import (
    load_watchlist,
    save_watchlist,
)

logger = get_logger(__name__)


# =====================================================
# CONFIG
# =====================================================

MAX_WATCHLIST_SIZE = 30

def _default_user_id() -> str:
    return str(settings.chat_id)


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


# =====================================================
# EXPORTS
# =====================================================


__all__ = [

    "normalize_symbol",

    "add_symbol",

    "remove_symbol",

    "get_watchlist",


]
