"""
Test helpers: synthetic price data and a patched market data provider.

Tests never touch the network. `offline_market()` replaces
yfinance.download with a deterministic random walk per symbol.
"""

from __future__ import annotations

import zlib
from contextlib import contextmanager
from unittest import mock

import numpy as np
import pandas as pd

PERIOD_ROWS = {"5d": 5, "1mo": 21, "6mo": 125, "1y": 250, "2y": 500}


def make_ohlcv(
    rows: int = 250,
    seed: int = 0,
    drift: float = 0.0005,
    vol: float = 0.02,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(drift, vol, rows)))
    spread = np.abs(rng.normal(0, vol / 2, rows))
    index = pd.bdate_range(end="2026-10-23", periods=rows)

    return pd.DataFrame(
        {
            "Open": close * (1 + rng.normal(0, vol / 4, rows)),
            "High": close * (1 + spread),
            "Low": close * (1 - spread),
            "Close": close,
            "Volume": rng.integers(1_000_000, 5_000_000, rows),
        },
        index=index,
    )


def fake_download(symbol, period="6mo", interval="1d", **kwargs):
    rows = PERIOD_ROWS.get(period, 125)
    full = make_ohlcv(rows=500, seed=zlib.crc32(symbol.encode()))
    return full.iloc[-rows:]


@contextmanager
def offline_market():
    from core.market import data

    data._PRICE_CACHE.clear()

    with mock.patch.object(data.yf, "download", side_effect=fake_download):
        yield

    data._PRICE_CACHE.clear()
