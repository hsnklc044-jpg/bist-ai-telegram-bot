"""
QuantBIST
Price data providers.

A provider downloads daily OHLCV candles. Everything else in the
system talks to the local store, so switching to a broker or paid
feed later means writing one new provider class.
"""

from __future__ import annotations

import warnings
from datetime import date
from typing import Protocol

import pandas as pd
import yfinance as yf

from core.infrastructure.logger import get_logger

logger = get_logger(__name__)

# yfinance still uses pandas' deprecated inplace=True internally; those
# warnings come from the library, not from QuantBIST, and flood the console.
warnings.filterwarnings(
    "ignore",
    message=".*inplace keyword.*",
    module=r"yfinance(\..*)?",
)

COLUMNS = ("open", "high", "low", "close", "volume")


class PriceProvider(Protocol):
    name: str

    def fetch(
        self,
        symbols: list[str],
        start: date,
    ) -> dict[str, pd.DataFrame]:
        """Daily candles from `start` until today, one frame per symbol."""


def normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """
    Lower-case OHLCV columns, tz-naive date index, no empty rows.
    """

    if df is None or df.empty:
        return pd.DataFrame(columns=list(COLUMNS))

    frame = df.copy()
    frame.columns = [str(c).strip().lower() for c in frame.columns]

    missing = [c for c in ("open", "high", "low", "close") if c not in frame.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    if "volume" not in frame.columns:
        frame["volume"] = 0.0

    frame = frame[list(COLUMNS)].apply(pd.to_numeric, errors="coerce")
    frame["volume"] = frame["volume"].fillna(0.0)

    index = pd.to_datetime(frame.index)
    if index.tz is not None:
        index = index.tz_localize(None)
    frame.index = index.normalize()
    frame.index.name = "date"

    frame = frame.dropna(subset=["open", "high", "low", "close"])
    frame = frame[~frame.index.duplicated(keep="last")]

    return frame.sort_index()


class YahooProvider:
    """Yahoo Finance via yfinance (BIST tickers end with .IS)."""

    name = "yahoo"

    def fetch(
        self,
        symbols: list[str],
        start: date,
    ) -> dict[str, pd.DataFrame]:
        if not symbols:
            return {}

        raw = yf.download(
            symbols,
            start=start.isoformat(),
            interval="1d",
            auto_adjust=True,
            group_by="ticker",
            progress=False,
            threads=True,
        )

        result: dict[str, pd.DataFrame] = {}

        for symbol in symbols:
            try:
                if isinstance(raw.columns, pd.MultiIndex):
                    if symbol not in raw.columns.get_level_values(0):
                        continue
                    frame = raw[symbol]
                else:
                    frame = raw

                frame = normalize_ohlcv(frame)

                if not frame.empty:
                    result[symbol] = frame
            except Exception as exc:  # noqa: BLE001
                logger.warning("Yahoo parse failed | %s | %s", symbol, exc)

        return result


_provider: PriceProvider = YahooProvider()


def get_provider() -> PriceProvider:
    return _provider


def set_provider(provider: PriceProvider) -> None:
    """Swap the data source (tests, or a future broker feed)."""

    global _provider
    _provider = provider


__all__ = [
    "COLUMNS",
    "PriceProvider",
    "YahooProvider",
    "normalize_ohlcv",
    "get_provider",
    "set_provider",
]
