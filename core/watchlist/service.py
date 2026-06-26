"""
QuantBIST RC4
Watchlist Service
"""

from __future__ import annotations

from core.watchlist.repository import (
    load_watchlist,
    save_watchlist,
)


def add_symbol(chat_id: int, symbol: str):

    symbol = symbol.upper().replace(".IS", "") + ".IS"

    data = load_watchlist()

    chat_id = str(chat_id)

    data.setdefault(chat_id, [])

    if symbol not in data[chat_id]:
        data[chat_id].append(symbol)

    save_watchlist(data)


def remove_symbol(chat_id: int, symbol: str):

    symbol = symbol.upper().replace(".IS", "") + ".IS"

    data = load_watchlist()

    chat_id = str(chat_id)

    if chat_id in data and symbol in data[chat_id]:
        data[chat_id].remove(symbol)

    save_watchlist(data)


def get_watchlist(chat_id: int):

    data = load_watchlist()

    return data.get(str(chat_id), [])