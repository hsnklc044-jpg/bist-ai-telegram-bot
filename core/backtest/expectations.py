"""
QuantBIST
What the technical views did in the past: the reference for the live measurement.

    python -m core.backtest.expectations --out data/view_expectations.csv

/performans scores each live record as "buy at the next open, hold 5, 20
or 60 sessions, minus XU100". This module scores every past day of every
stock the same way, with the same score (the indicators only look back),
on point-in-time BIST 100 members (a stock counts only on days it was a
member). The live result can then be read against what the backtest
period showed.

The figures are a reference, not a test: holding periods overlap and the
period is the one all research was done on. A live result close to the
reference says nothing is broken; it does not prove the view works.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
import pandas as pd

from core.backtest.research import DEFAULT_START, _universe
from core.backtest.run import load_frames
from core.config.paths import DATA_DIR
from core.config.thresholds import SIGNAL_VIEW_LABELS
from core.market.calendar import now_istanbul
from core.market.universe import BENCHMARK
from core.strategy.score import score_frame

HORIZONS = (5, 20, 60)
EXPECTATIONS_FILE = DATA_DIR / "view_expectations.csv"
FIELDS = ("view", "horizon", "mean", "hit_rate", "days", "records", "period_start", "period_end",
          "universe", "generated")


def view_excess(df: pd.DataFrame, bench: pd.DataFrame, horizons=HORIZONS) -> pd.DataFrame:
    """
    One row per (day, horizon) of one stock: its view that evening and the return of buying at
    the next open and selling at the close `horizon` sessions later, minus XU100 over the same
    sessions (core.reports.forward.forward_excess, vectorized).
    """

    scores = score_frame(df)
    views = scores["signal"].map(SIGNAL_VIEW_LABELS)
    b_open = bench["open"].reindex(df.index)
    b_close = bench["close"].reindex(df.index)
    out = []
    for h in horizons:
        entry_open, entry_bench = df["open"].shift(-1), b_open.shift(-1)
        own = df["close"].shift(-h) / entry_open - 1
        market = b_close.shift(-h) / entry_bench - 1
        part = pd.DataFrame({"view": views, "excess": own - market, "horizon": h})
        out.append(part[scores["score"].notna() & part["excess"].notna() & np.isfinite(part["excess"])])
    result = pd.concat(out) if out else pd.DataFrame(columns=["view", "excess", "horizon"])
    result.index.name = "day"
    return result.reset_index()


def expectations(frames, bench, eligible=None, start: str = DEFAULT_START, end=None,
                 horizons=HORIZONS) -> pd.DataFrame:
    parts = []
    for symbol, df in frames.items():
        rows = view_excess(df, bench, horizons)
        rows = rows[rows["day"] >= pd.Timestamp(start)]
        if end is not None:
            rows = rows[rows["day"] <= pd.Timestamp(end)]
        if eligible is not None:
            member = eligible[symbol] if symbol in eligible.columns else pd.Series(False, index=eligible.index)
            rows = rows[member.reindex(rows["day"]).fillna(False).to_numpy(dtype=bool)]
        parts.append(rows)
    rows = pd.concat(parts) if parts else pd.DataFrame(columns=["day", "view", "excess", "horizon"])
    table = []
    for (view, h), part in rows.groupby(["view", "horizon"]):
        daily = part.groupby("day")["excess"].mean()  # same-day records move together
        table.append({
            "view": view, "horizon": int(h), "mean": float(daily.mean()),
            "hit_rate": float((part["excess"] > 0).mean()), "days": int(len(daily)), "records": int(len(part)),
            "period_start": rows["day"].min().date().isoformat(), "period_end": rows["day"].max().date().isoformat(),
        })
    return pd.DataFrame(table)


def write(table: pd.DataFrame, path: Path, universe: str) -> None:
    stamp = now_istanbul().date().isoformat()
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in table.to_dict("records"):
            writer.writerow({**row, "mean": f"{row['mean']:.6f}", "hit_rate": f"{row['hit_rate']:.4f}",
                             "universe": universe, "generated": stamp})


def load(path: Path | str | None = None) -> dict[tuple[str, int], dict]:
    """(view, horizon) -> row; empty when the file is missing or unreadable."""

    path = Path(path or EXPECTATIONS_FILE)
    try:
        with open(path, encoding="utf-8", newline="") as fh:
            return {(r["view"], int(r["horizon"])): {**r, "mean": float(r["mean"]), "hit_rate": float(r["hit_rate"])}
                    for r in csv.DictReader(fh)}
    except (OSError, ValueError, KeyError):
        return {}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Past results of the technical views (live reference).")
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    frames, _, eligible = _universe("pit")
    bench = load_frames([BENCHMARK])[BENCHMARK]
    table = expectations(frames, bench, eligible, start=args.start)
    order = {v: i for i, v in enumerate(SIGNAL_VIEW_LABELS.values())}
    table = table.sort_values(["horizon", "view"], key=lambda c: c.map(order) if c.name == "view" else c)
    print(f"Teknik görünümlerin geçmişi (geçmiş BIST 100 üyeliği, {len(frames)} hisse, {args.start} – son)")
    print("Sonraki seansın açılışında alıp h seans tutmak, XU100'e göre fark; gün ortalamalarının ortalaması")
    for row in table.itertuples():
        print(f"  {row.horizon:>2} seans  {row.view:<14} {row.mean * 100:+6.2f}%  isabet %{row.hit_rate * 100:.0f}  "
              f"{row.days} gün, {row.records} kayıt")
    if args.out:
        write(table, args.out, "pit")
        print(f"Yazıldı: {args.out}")


if __name__ == "__main__":
    main()


__all__ = ["EXPECTATIONS_FILE", "expectations", "load", "view_excess", "write"]
