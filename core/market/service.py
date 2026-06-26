"""
QuantBIST RC4
Market Service
"""

from __future__ import annotations


def get_market_status() -> dict:
    """
    Dashboard ve Telegram için market bilgisi.
    """

    return {

        "status": "OPEN",

        "index": "BIST100",

        "change": "+1.24",

        "trend": "BULLISH",

    }