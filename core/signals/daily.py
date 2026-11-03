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


def filter_on(day: date) -> bool:
    """The ML filter may record signals only after its out-of-sample pass (K-59) AND with the model
    gate open: a current independent validation of M30 (K-70 madde 5)."""

    from core.ml import ml_filter
    from core.reports import model_gate

    return ml_filter.enabled() and model_gate.allowed("M30", day)


def run(day: date, bars, frames: dict[str, pd.DataFrame] | None = None, path=None, enabled=None,
        probabilities=None) -> str:
    """One daily step; returns the summary line. `bars(symbol)`: final daily candles."""

    from pathlib import Path

    from core.config.paths import SIGNALS_DB
    from core.ml import ml_filter
    from core.signals import panic, store

    if panic.active():
        logger.warning("Signal book step skipped: panic lock")
        return "⛔ Panik kilidi açık: sinyal defteri durduruldu (/devam ile kalkar)."
    enabled = (lambda: filter_on(day)) if enabled is None else enabled
    if not Path(path or SIGNALS_DB).exists() and not enabled():
        return ""  # no book yet and nothing could be recorded: no file is created
    conn = store.connect(path)
    try:
        store.expire_pending(conn, day)
        store.update(conn, bars)
        store.check_breaker(conn, day)
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


__all__ = ["run"]
