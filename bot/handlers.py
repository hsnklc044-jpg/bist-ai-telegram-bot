"""
QuantBIST RC4
Handler Registry
"""

from __future__ import annotations

from telegram.ext import (
    Application,
    CommandHandler,
)

from bot.start import start
from bot.reports import summary
from bot.analysis import (
    top,
    analyze,
)
from bot.watchlist import (
    watchadd,
    watchremove,
    watchlist,
    watchscan,
)


def register_handlers(app: Application) -> None:
    """Register Telegram handlers."""

    handlers = [

        ("start", start),

        ("summary", summary),

        ("top", top),

        ("analyze", analyze),

        ("watchadd", watchadd),

        ("watchremove", watchremove),

        ("watchlist", watchlist),

        ("watchscan", watchscan),

    ]

    for command, callback in handlers:

        app.add_handler(
            CommandHandler(
                command,
                callback,
            )
        )