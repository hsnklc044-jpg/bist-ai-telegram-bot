"""
Test helpers: synthetic price data and an offline market.

Tests never touch the network. `offline_market()` swaps the price
provider for a deterministic random walk per symbol and points the
price store at a temporary database.
"""

from __future__ import annotations

import tempfile
import zlib
from contextlib import contextmanager
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

HISTORY_ROWS = 600
LAST_DAY = "2026-10-23"


def make_ohlcv(
    rows: int = 250,
    seed: int = 0,
    drift: float = 0.0005,
    vol: float = 0.02,
    end: str = LAST_DAY,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(drift, vol, rows)))
    spread = np.abs(rng.normal(0, vol / 2, rows))
    index = pd.bdate_range(end=end, periods=rows)

    open_ = close * (1 + rng.normal(0, vol / 4, rows))
    volume = rng.integers(1_000_000, 5_000_000, rows).astype(float)  # same draw order as before

    # the open stays inside the high–low range, as on a real candle (validation M16 checks it)
    return pd.DataFrame(
        {
            "open": open_,
            "high": np.maximum(close * (1 + spread), open_),
            "low": np.minimum(close * (1 - spread), open_),
            "close": close,
            "volume": volume,
        },
        index=index,
    )


class FakeProvider:
    """Deterministic prices; records every request."""

    name = "fake"

    def __init__(self, rows: int = HISTORY_ROWS, fail: bool = False):
        self.rows = rows
        self.fail = fail
        self.calls: list[tuple[tuple[str, ...], date]] = []
        self.overrides: dict[str, pd.DataFrame] = {}

    def frame(self, symbol: str) -> pd.DataFrame:
        if symbol in self.overrides:
            return self.overrides[symbol]

        return make_ohlcv(rows=self.rows, seed=zlib.crc32(symbol.encode()))

    def fetch(self, symbols, start):
        self.calls.append((tuple(symbols), start))

        if self.fail:
            raise ConnectionError("provider offline")

        result = {}
        for symbol in symbols:
            df = self.frame(symbol)
            result[symbol] = df[df.index >= pd.Timestamp(start)]

        return result


@contextmanager
def offline_market(provider: FakeProvider | None = None):
    from core.market import data, store
    from core.market import provider as provider_module

    provider = provider or FakeProvider()
    previous_provider = provider_module.get_provider()
    previous_db = store._db_path

    with tempfile.TemporaryDirectory() as tmp:
        store.configure(Path(tmp) / "market.db")
        provider_module.set_provider(provider)
        data.clear_cache()

        try:
            yield provider
        finally:
            provider_module.set_provider(previous_provider)
            store.configure(previous_db)
            data.clear_cache()
