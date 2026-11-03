"""
QuantBIST
The paper signal book's daily step (K-60), after the report: follow the open signals with the
day's final candles, check the 6% breaker, then (only when the ML filter passed its
out-of-sample test, K-59) record today's signals of the BIST 30 approximation.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from core.infrastructure.logger import get_logger

logger = get_logger(__name__)


def run(day: date, bars, frames: dict[str, pd.DataFrame] | None = None, path=None, enabled=None,
        probabilities=None) -> str:
    """One daily step; returns the summary line. `bars(symbol)`: final daily candles."""

    from core.ml import ml_filter
    from core.signals import store

    enabled = ml_filter.enabled if enabled is None else enabled
    conn = store.connect(path)
    try:
        store.update(conn, bars)
        sessions = [d for d in _sessions(conn, bars) if d <= pd.Timestamp(day)]
        if len(sessions) >= 2:
            store.check_breaker(conn, bars, sessions[-1].date(), sessions[-2].date())
        added = 0
        if enabled() and frames and not store.blocked(conn, day):
            if probabilities is None:
                from core.ml.live import probabilities
            for symbol, p in sorted(probabilities(frames).items()):
                if p >= ml_filter.PROBA and frames[symbol].index[-1].date() == day:
                    added += store.add(conn, day, symbol, float(frames[symbol]["close"].iloc[-1]), p) is not None
        logger.info("Signal book | new %d", added)
        return store.summary(conn, bars, day)
    finally:
        conn.close()


def _sessions(conn, bars) -> list[pd.Timestamp]:
    """The sessions of the stocks in the book (their own candles)."""

    from core.signals import store

    days: set[pd.Timestamp] = set()
    for s in store.signals(conn):
        df = bars(s.symbol)
        if df is not None and not df.empty:
            days |= set(df.index[-15:])
    return sorted(days)


__all__ = ["run"]
