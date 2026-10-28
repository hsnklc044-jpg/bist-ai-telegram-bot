"""
QuantBIST
Do the support/resistance levels mean anything? A DESCRIPTIVE measurement (Özellik A §3.3,
DECISIONS K-49): not a hypothesis, no research budget, no holdout (the screening period only).

When a close comes within APPROACH_ATR of a cluster level known that day, the next HORIZON
closes decide: "dönüş" (1 ATR away in the direction the price came from), "kırılma" (0.5 ATR
through the level) or "belirsiz" (neither). The same is done for the same number of random fake
levels drawn uniformly in that day's 52-week [low, high] (fixed seed). If real levels turn the
price no more often than fake ones, every level is shown with "tarihsel olarak rastgele
seviyeden ayırt edilemedi".

    python -m core.analytics.levels_study       # the GitHub Actions run prints it
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from core.analytics import levels as L

APPROACH_ATR = 0.25
TURN_ATR = 1.0
HORIZON = 5
BLOCK = 20  # sessions per bootstrap block
SAMPLES = 2000
OUTCOMES = ("dönüş", "kırılma", "belirsiz")


def outcome(after: np.ndarray, level: float, atr: float, from_above: bool) -> str:
    """The first of: 1 ATR back where the price came from, or 0.5 ATR through the level."""

    for c in after:
        if from_above:
            if c < level - L.BREAK_ATR * atr:
                return "kırılma"
            if c >= level + TURN_ATR * atr:
                return "dönüş"
        else:
            if c > level + L.BREAK_ATR * atr:
                return "kırılma"
            if c <= level - TURN_ATR * atr:
                return "dönüş"
    return "belirsiz"


def _empty() -> dict:
    return {"n": 0, **dict.fromkeys(OUTCOMES, 0)}


@dataclass
class StockResult:
    real: dict = field(default_factory=_empty)
    fake: dict = field(default_factory=_empty)
    days: dict = field(default_factory=dict)  # day -> [real n, real turns, fake n, fake turns]

    @property
    def real_rate(self) -> float:
        return self.real["dönüş"] / self.real["n"] if self.real["n"] else float("nan")

    @property
    def fake_rate(self) -> float:
        return self.fake["dönüş"] / self.fake["n"] if self.fake["n"] else float("nan")


def _events(close: np.ndarray, d: int, a: float, levels_today, side: str, out: dict, day_row: list, offset: int):
    for level in levels_today:
        if abs(close[d] - level) >= APPROACH_ATR * a or close[d - 1] == level:
            continue
        result = outcome(close[d + 1:d + 1 + HORIZON], level, a, from_above=close[d - 1] > level)
        out["n"] += 1
        out[result] += 1
        day_row[offset] += 1
        day_row[offset + 1] += result == "dönüş"


def study_stock(df: pd.DataFrame, rng: np.random.Generator, eligible: np.ndarray | None = None,
                first_event: int = 0, last_event: int | None = None) -> StockResult:
    """Every approach of one stock. Levels on day d use candles up to d only; the outcome uses
    the next HORIZON closes (the measurement, not the level, looks ahead)."""

    close = df["close"].to_numpy(dtype=float)
    high52 = df["high"].rolling(L.LOOKBACK, min_periods=1).max().to_numpy()
    low52 = df["low"].rolling(L.LOOKBACK, min_periods=1).min().to_numpy()
    last_event = len(df) - HORIZON - 1 if last_event is None else min(last_event, len(df) - HORIZON - 1)
    result = StockResult()
    for d, a, groups in L.cluster_days(df):
        if groups is None or not groups or d < max(first_event, 1) or d > last_event:
            continue
        if eligible is not None and not eligible[d]:
            continue
        real = [price for price, _ in groups]
        fake = rng.uniform(low52[d], high52[d], size=len(real))
        row = result.days.setdefault(df.index[d], [0, 0, 0, 0])
        _events(close, d, a, real, "real", result.real, row, 0)
        _events(close, d, a, fake, "fake", result.fake, row, 2)
    return result


def _interval(days: pd.DataFrame, seed: int = 0) -> tuple[float, float]:
    """95% block bootstrap of (real turn rate − fake turn rate) over the event days."""

    values = days[["rn", "rt", "fn", "ft"]].to_numpy(dtype=float)
    n = len(values)
    if n < 2 * BLOCK:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    blocks = int(np.ceil(n / BLOCK))
    starts = rng.integers(0, n, size=(SAMPLES, blocks))
    index = ((starts[:, :, None] + np.arange(BLOCK)) % n).reshape(SAMPLES, -1)[:, :n]
    sums = values[index].sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        diff = sums[:, 1] / sums[:, 0] - sums[:, 3] / sums[:, 2]
    low, high = np.nanquantile(diff, [0.025, 0.975])
    return float(low), float(high)


def study(data, start: str | None = None) -> dict:
    """Every stock of the card's data (frames, bench, eligible), from HISTORY_START to SCREEN_END."""

    from core.backtest.run import SCREEN_END
    from core.screen.card import HISTORY_START

    frames, bench, eligible = data
    start = pd.Timestamp(start or HISTORY_START)
    total_real, total_fake, rows = _empty(), _empty(), {}
    for i, (symbol, df) in enumerate(sorted(frames.items())):
        df = df.loc[:SCREEN_END]
        if df.empty:
            continue
        ok = None
        if eligible is not None and symbol in eligible.columns:
            ok = eligible[symbol].reindex(df.index).ffill().fillna(False).astype(bool).to_numpy()
        first = int(df.index.searchsorted(start))
        r = study_stock(df, np.random.default_rng(1000 + i), ok, first_event=first)
        for k in total_real:
            total_real[k] += r.real[k]
            total_fake[k] += r.fake[k]
        for day, row in r.days.items():
            acc = rows.setdefault(day, [0, 0, 0, 0])
            for j in range(4):
                acc[j] += row[j]
    days = pd.DataFrame.from_dict(rows, orient="index", columns=["rn", "rt", "fn", "ft"]).sort_index()
    low, high = _interval(days) if len(days) else (float("nan"), float("nan"))
    real_rate = total_real["dönüş"] / total_real["n"] if total_real["n"] else float("nan")
    fake_rate = total_fake["dönüş"] / total_fake["n"] if total_fake["n"] else float("nan")
    return {"real": total_real, "fake": total_fake, "real_rate": real_rate, "fake_rate": fake_rate,
            "low": low, "high": high, "days": len(days)}


def verdict(r: dict) -> str:
    if not r["low"] == r["low"]:
        return "yetersiz örnek"
    if r["low"] > 0:
        return "tarihsel olarak gerçek seviyeler rastgele seviyelerden daha sık dönüş gördü (tanımlayıcı; kanıt değildir)"
    if r["high"] < 0:
        return "tarihsel olarak gerçek seviyeler rastgele seviyelerden daha seyrek dönüş gördü (tanımlayıcı)"
    return "tarihsel olarak rastgele seviyeden ayırt edilemedi"


def study_text(data=None) -> str:
    from core.screen import command

    r = study(data if data is not None else command._history_data())

    def share(part: dict, key: str) -> str:
        return f"%{part[key] / part['n'] * 100:.1f}".replace(".", ",") if part["n"] else "—"

    lines = [f"Destek/direnç anlamlılık ölçümü (tanımlayıcı ölçüm; hipotez değil, bütçe dışı; K-49): "
             f"yaklaşma < {APPROACH_ATR:g} ATR, sonraki {HORIZON} seans, tarama dönemi, holdout yok".replace(".", ",")]
    for name, part in (("gerçek küme seviyeleri", r["real"]), ("rastgele seviyeler (52 hafta aralığı)", r["fake"])):
        lines.append(f"  {name}: {part['n']} yaklaşma · dönüş {share(part, 'dönüş')} · kırılma "
                     f"{share(part, 'kırılma')} · belirsiz {share(part, 'belirsiz')}")
    if r["low"] == r["low"]:
        gap = (r["real_rate"] - r["fake_rate"]) * 100
        lines.append(f"  dönüş farkı (gerçek − rastgele): {gap:+.1f} puan, %95 [{r['low'] * 100:+.1f}, "
                     f"{r['high'] * 100:+.1f}] ({r['days']} gün, {BLOCK} seanslık blok bootstrap)".replace(".", ","))
    lines.append(f"  → {verdict(r)}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    from core.infrastructure.console import utf8_output

    utf8_output()
    print(study_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["outcome", "study", "study_stock", "study_text", "verdict"]
