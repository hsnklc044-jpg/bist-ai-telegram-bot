"""
QuantBIST RC4
Watchlist Repository
"""

from __future__ import annotations

import json
from pathlib import Path

WATCHLIST_FILE = Path("data/watchlist.json")


def load_watchlist() -> dict:

    if not WATCHLIST_FILE.exists():

        WATCHLIST_FILE.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        WATCHLIST_FILE.write_text(
            "{}",
            encoding="utf-8",
        )

    return json.loads(
        WATCHLIST_FILE.read_text(
            encoding="utf-8"
        )
    )


def save_watchlist(data: dict) -> None:

    WATCHLIST_FILE.write_text(
        json.dumps(
            data,
            indent=4,
        ),
        encoding="utf-8",
    )