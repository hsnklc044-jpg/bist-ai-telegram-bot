"""Professional technical score, 0–100 (I, the user's 11.11.2026 decision; DECISIONS K-88).

The thresholds were written on 11.11.2026 before any result was seen and are not tuned afterwards.

| Dimension | Points | Rule |
|---|---|---|
| Long trend | 20 | close > SMA200 (10); SMA50 > SMA200 (10) |
| Medium momentum | 20 | 12-month return excl. last month > 0 (10); 6-month excl. last month > 0 (10) |
| Relative strength | 20 | percentile of rs_puan in the universe ≥ 70 (20), 30–69 (10), < 30 (0) |
| Near the 52-week high | 15 | within 10 % (15), within 25 % (7), further (0) |
| Short confirmation | 15 | MACD > signal (5); 50 ≤ RSI ≤ 70 (5); close > EMA20 (5) |
| Volume confirmation | 10 | OBV slope > 0 (5); CMF > 0 (5) |

Volatility rank ≥ 90 is a warning (⚠️), not points. A dimension with a missing input is "veri yok": not counted as 0,
and a score with a missing dimension gets no colour ("N/100 (eksik boyut: …)"). Every input is a /tara field
(core/screen/fields.py): one calculation in one place. The user's scorecard (core/analytics/scorecard.py) is separate
and unchanged. A technical description, not a recommendation."""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from core.reports.style import score_class

VOLATILITY_WARNING = 90


@dataclass(frozen=True)
class Dimension:
    name: str
    maximum: int
    inputs: tuple[str, ...]
    points: Callable[[pd.Series], int]


def _rs(r: pd.Series) -> int:
    rank = r["goreli_guc_yuzdelik"]
    return 20 if rank >= 70 else 10 if rank >= 30 else 0


def _high(r: pd.Series) -> int:
    distance = -r["zirve_uzaklik"]  # the field is close / high − 1, in %, so ≤ 0
    return 15 if distance <= 10 else 7 if distance <= 25 else 0


DIMENSIONS = (
    Dimension("Uzun vadeli trend", 20, ("close", "sma(200)", "sma(50)"),
              lambda r: 10 * (r["close"] > r["sma(200)"]) + 10 * (r["sma(50)"] > r["sma(200)"])),
    Dimension("Orta vadeli momentum", 20, ("getiri_12a_1a_haric", "getiri_6a_1a_haric"),
              lambda r: 10 * (r["getiri_12a_1a_haric"] > 0) + 10 * (r["getiri_6a_1a_haric"] > 0)),
    Dimension("Göreli güç", 20, ("goreli_guc_yuzdelik",), _rs),
    Dimension("52 hafta zirvesine yakınlık", 15, ("zirve_uzaklik",), _high),
    Dimension("Kısa vadeli teyit", 15, ("macd", "macd_sinyal", "rsi", "close", "ema20"),
              lambda r: 5 * (r["macd"] > r["macd_sinyal"]) + 5 * (50 <= r["rsi"] <= 70) + 5 * (r["close"] > r["ema20"])),
    Dimension("Hacim teyidi", 10, ("obv_egim", "cmf"), lambda r: 5 * (r["obv_egim"] > 0) + 5 * (r["cmf"] > 0)),
)
COLUMNS = tuple(dict.fromkeys(c for d in DIMENSIONS for c in d.inputs if c != "close")) + ("oynaklik_sira",)


def _missing(value) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


@dataclass
class ProScore:
    parts: dict[str, int | None] = field(default_factory=dict)
    warning: bool = False

    @property
    def total(self) -> int:
        return int(sum(p for p in self.parts.values() if p is not None))

    @property
    def missing(self) -> list[str]:
        return [name for name, p in self.parts.items() if p is None]

    def label(self) -> str:
        text = f"{self.total}/100"
        return text + (f" (eksik boyut: {', '.join(self.missing)})" if self.missing else "")

    def colour(self) -> tuple[str, str] | None:
        return None if self.missing else score_class(self.total)


def score(row: pd.Series) -> ProScore:
    """One stock's latest field values (a row of core.screen.fields.table with the ranked columns filled)."""

    result = ProScore()
    for d in DIMENSIONS:
        values = [row.get(c) for c in d.inputs]
        result.parts[d.name] = None if any(_missing(v) for v in values) else int(d.points(row))
    vol = row.get("oynaklik_sira")
    result.warning = not _missing(vol) and vol >= VOLATILITY_WARNING
    return result


def totals(frame: pd.DataFrame) -> pd.Series:
    """The score of every row of a field table (with "close"), vectorised; NaN where a dimension is missing.
    Same rules as score() (tested against it); used for the past classes of /karne."""

    total = pd.Series(0.0, index=frame.index)
    missing = pd.Series(False, index=frame.index)
    f = frame
    gt = lambda a, b: (f[a] > f[b]).astype(float)  # noqa: E731
    parts = {
        "Uzun vadeli trend": 10 * gt("close", "sma(200)") + 10 * gt("sma(50)", "sma(200)"),
        "Orta vadeli momentum": 10 * (f["getiri_12a_1a_haric"] > 0) + 10 * (f["getiri_6a_1a_haric"] > 0),
        "Göreli güç": np.where(f["goreli_guc_yuzdelik"] >= 70, 20, np.where(f["goreli_guc_yuzdelik"] >= 30, 10, 0)),
        "52 hafta zirvesine yakınlık": np.where(-f["zirve_uzaklik"] <= 10, 15, np.where(-f["zirve_uzaklik"] <= 25, 7, 0)),
        "Kısa vadeli teyit": 5 * gt("macd", "macd_sinyal") + 5 * f["rsi"].between(50, 70) + 5 * gt("close", "ema20"),
        "Hacim teyidi": 5 * (f["obv_egim"] > 0) + 5 * (f["cmf"] > 0),
    }
    for d in DIMENSIONS:
        missing |= f[list(d.inputs)].isna().any(axis=1)
        total += pd.Series(parts[d.name], index=f.index).astype(float)
    return total.where(~missing)


def latest_rows(frames: dict[str, pd.DataFrame], bench_close: pd.Series,
                universe: dict[str, pd.DataFrame] | None = None) -> dict[str, pd.Series]:
    """Each stock's score on its last closed candle. The ranked fields (relative strength, volatility) are ranked
    in `universe` (the BIST 100 frames) when given, else among `frames`; a stock outside the universe gets the
    share of universe values at or below its own."""

    from core.screen import fields

    ranked = [c for c in COLUMNS if c in fields.RANKED]
    base_cols = list(dict.fromkeys([*COLUMNS, *(fields.RANKED[c] for c in ranked)]))

    def tables(group):
        return {s: fields.table(df, bench_close, base_cols, recent=1) for s, df in group.items() if len(df)}

    own = tables(frames)
    if universe is None:
        fields.rank_last(own, ranked)
    else:
        members = tables({s: df for s, df in universe.items() if s not in own}) | {s: t for s, t in own.items()
                                                                                  if s in universe}
        fields.rank_last(members, ranked)
        for column in ranked:
            base = pd.Series({s: t[fields.RANKED[column]].iloc[-1] for s, t in members.items()}, dtype=float).dropna()
            for s, t in own.items():
                if s in universe:
                    continue
                value = t[fields.RANKED[column]].iloc[-1]
                t.loc[t.index[-1], column] = (base <= value).mean() * 100 if len(base) and pd.notna(value) else math.nan
    out = {}
    for s, t in own.items():
        r = t.iloc[-1].copy()
        r["close"] = float(frames[s]["close"].iloc[-1])
        out[s] = r
    return out


def latest(frames: dict[str, pd.DataFrame], bench_close: pd.Series,
           universe: dict[str, pd.DataFrame] | None = None) -> dict[str, ProScore]:
    return {s: score(r) for s, r in latest_rows(frames, bench_close, universe).items()}


__all__ = ["COLUMNS", "DIMENSIONS", "Dimension", "ProScore", "VOLATILITY_WARNING", "latest", "latest_rows", "score", "totals"]
