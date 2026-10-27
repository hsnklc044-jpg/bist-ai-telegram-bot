"""
QuantBIST
Market Data

Public entry point for price history. Reads from the local store
(core.market.store), refreshing it from the provider when needed,
and only ever returns final (closed) daily candles.
"""

from __future__ import annotations

import threading
from datetime import datetime, timedelta

import pandas as pd

from core.infrastructure.exceptions import MarketError
from core.infrastructure.logger import get_logger
from core.market import store
from core.market.calendar import drop_open_candle
from core.market.corrections import clean

logger = get_logger(__name__)

DEFAULT_PERIOD = "2y"
CACHE_MINUTES = 5

PERIOD_DAYS = {
    "5d": 7,
    "1mo": 31,
    "3mo": 92,
    "6mo": 183,
    "1y": 366,
    "2y": 731,
    "5y": 1827,
    "max": 365 * 50,
}

_cache: dict[str, tuple[datetime, pd.DataFrame]] = {}
_cache_lock = threading.Lock()


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()


def _history(symbol: str) -> pd.DataFrame:
    """Full stored history of closed candles, refreshed if stale."""

    now = datetime.now()

    with _cache_lock:
        item = _cache.get(symbol)
        if item and now - item[0] < timedelta(minutes=CACHE_MINUTES):
            return item[1]

    status = store.update([symbol], now=now).get(symbol)
    df = drop_open_candle(clean(store.read(symbol), symbol))

    if df.empty:
        raise MarketError(f"No price data: {symbol} ({status})")

    if status == "failed":
        logger.warning(
            "Using stored data, provider unavailable | %s | last=%s",
            symbol,
            df.index[-1].date(),
        )

    with _cache_lock:
        _cache[symbol] = (now, df)

    return df


def load_price_history(
    symbol: str,
    period: str = DEFAULT_PERIOD,
    interval: str = "1d",
) -> pd.DataFrame:
    """
    Daily closed candles: columns open, high, low, close, volume.

    The returned frame is a copy; callers may modify it.
    """

    if interval != "1d":
        raise MarketError("Only daily candles are supported.")

    if period not in PERIOD_DAYS:
        raise MarketError(f"Unknown period: {period}")

    df = _history(symbol)
    start = df.index[-1] - pd.Timedelta(days=PERIOD_DAYS[period])

    return df[df.index > start].copy()


def preload(symbols: list[str]) -> dict[str, str]:
    """Update many symbols in one provider request (faster than one by one)."""

    status = store.update(symbols)
    clear_cache()

    return status


__all__ = [
    "DEFAULT_PERIOD",
    "PERIOD_DAYS",
    "clear_cache",
    "load_price_history",
    "preload",
]
