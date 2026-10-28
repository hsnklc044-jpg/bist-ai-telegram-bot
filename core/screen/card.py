"""
QuantBIST
The /tara history card: the same query on 2023-08-01 – 30.10.2026 (the research period). The
holdout (from 02.11.2026) is never read: load_frames cuts the data, and the card cuts it again
here. Each day the query held for a stock that was a BIST 100 member that day: buy at the next
session's open, sell at the close `h` sessions later, minus XU100 over the same sessions.

It describes the past. Queries can be tried freely, so it is not evidence that a rule works
(no research budget, no pre-registration; docs/RESEARCH_PROGRAM.md).
"""

from __future__ import annotations

import pandas as pd

from core.screen import fields as F
from core.screen.language import Query

HISTORY_START = "2023-08-01"
HORIZONS = (5, 20)
MIN_SAMPLES = 30


def _tables(query: Query, frames: dict, bench: pd.DataFrame, eligible: pd.DataFrame | None) -> dict:
    wanted = sorted(query.fields) or ["kapanis"]
    tables = {s: F.table(df, bench["close"], wanted) for s, df in frames.items() if not df.empty}
    if "gg_sira" in query.fields and tables:
        panel = pd.DataFrame({s: t["gg_60"] for s, t in tables.items()})
        if eligible is not None:
            ok = eligible.reindex(index=panel.index, columns=panel.columns).ffill().fillna(False).astype(bool)
            panel = panel.where(ok)
        ranks = panel.rank(axis=1, pct=True) * 100
        for s, t in tables.items():
            t["gg_sira"] = ranks[s].reindex(t.index)
    return tables


def history(query: Query, frames: dict[str, pd.DataFrame], bench: pd.DataFrame,
            eligible: pd.DataFrame | None = None, horizons=HORIZONS) -> dict[int, tuple]:
    """{horizon: (mean excess, hit rate, samples)}; (None, None, 0) without samples."""

    from core.backtest.run import SCREEN_END

    bench = bench.loc[:SCREEN_END]
    frames = {s: df.loc[:SCREEN_END] for s, df in frames.items()}
    tables = _tables(query, frames, bench, eligible)
    collected: dict[int, list[pd.Series]] = {h: [] for h in horizons}
    for symbol, table in tables.items():
        df = frames[symbol]
        mask = query.mask(table) & (table.index >= pd.Timestamp(HISTORY_START))
        if eligible is not None:
            if symbol not in eligible.columns:
                continue
            mask &= eligible[symbol].reindex(table.index).ffill().fillna(False).astype(bool)
        if not mask.any():
            continue
        b = bench.reindex(df.index)
        entry, bench_entry = df["open"].shift(-1), b["open"].shift(-1)
        for h in horizons:
            excess = (df["close"].shift(-h) / entry - 1) - (b["close"].shift(-h) / bench_entry - 1)
            collected[h].append(excess[mask].dropna())
    card = {}
    for h, parts in collected.items():
        values = pd.concat(parts) if parts else pd.Series(dtype=float)
        n = int(len(values))
        card[h] = (float(values.mean()), float((values > 0).mean()), n) if n else (None, None, 0)
    return card


__all__ = ["HISTORY_START", "HORIZONS", "MIN_SAMPLES", "history"]
