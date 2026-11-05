"""
QuantBIST
K-78 measurement: monthly returns, costs, the interval and the verdict, exactly as DECISIONS K-78 fixed them
before any return was computed (05.11.2026). The month itself (universe, slices, applicability) is
core.analytics.factor_study.month; this module only adds what happens after the formation day.

Nothing here runs on real data by itself. The measurement is one Actions run on two frozen daily snapshots
(K-78 "İki indirme"); until then only the synthetic tests in tests/test_factor_measure.py use it.

- holding: buy at the entry day's open, sell at the entry month's last market day close
  (factor_study.exit_fill: a lower-limit lock moves the exit to the first unlocked open; HOLDOUT_START and
  later are never read);
- portfolio: equal weight; cost 0.15% on the bought and 0.15% on the sold part of the weight change from
  the previous month's target weights (drift inside a month is not modelled; the same for slice and universe);
- excess: slice net return − universe net return, same month, same applicability rules;
- interval: moving block bootstrap, 3-month blocks, 10,000 draws, seed 0; one-sided 97.5% lower bound
  (Bonferroni, 2 factors); the two-sided 95% upper end decides "excluded" against "unanswered".
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd

from core.analytics import factor_study as F

COST_BUY = COST_SELL = 0.0015
COST_INFO = 0.0030          # information line only; never changes the verdict
BLOCK, DRAWS, SEED = 3, 10_000, 0
LITERATURE = 0.005          # monthly; an upper end below it excludes a literature-sized effect
YEARS = (2023, 2024, 2025)

PASSED = "KEŞİFTE GEÇTİ"
EXCLUDED = "GEÇMEDİ (literatür büyüklüğünde bir etki dışlandı)"
UNANSWERED = "YANITLANAMADI (güç yetersiz)"
UNMEASURED = "ÖLÇÜLEMEDİ"
SENSITIVE = "VERİYE DUYARLI"


def holding(frames: dict[str, pd.DataFrame], names: list[str], entry: date, days: pd.DatetimeIndex,
            stop=None) -> tuple[dict[str, float], list[str]]:
    """Gross return of each name from the entry open to its exit, and the exit notes."""

    entry_ts = pd.Timestamp(entry)
    month_days = days[days.to_period("M") == entry_ts.to_period("M")]
    last = month_days[-1].date()
    out, notes = {}, []
    for s in names:
        df = frames[s]
        bought = float(df.at[entry_ts, "open"])
        fill = F.exit_fill(df, entry, last, stop)
        if fill is None or not bought:
            continue
        out[s] = fill[1] / bought - 1
        if fill[2]:
            notes.append(f"{s} {fill[0]}: {fill[2]}")
    return out, notes


def cost(new: list[str], old: list[str], buy: float = COST_BUY, sell: float = COST_SELL) -> float:
    """Equal-weight target change from `old` to `new`: buy cost on weight added, sell cost on weight removed."""

    w_new = {s: 1 / len(new) for s in new} if new else {}
    w_old = {s: 1 / len(old) for s in old} if old else {}
    names = set(w_new) | set(w_old)
    up = sum(max(w_new.get(s, 0) - w_old.get(s, 0), 0) for s in names)
    down = sum(max(w_old.get(s, 0) - w_new.get(s, 0), 0) for s in names)
    return buy * up + sell * down


@dataclass
class Series:
    """One factor's monthly record (holding month → values); invalid months are left out."""

    months: list[pd.Period] = field(default_factory=list)
    slice_net: list[float] = field(default_factory=list)
    universe_net: list[float] = field(default_factory=list)
    excess: list[float] = field(default_factory=list)
    excess_high_cost: list[float] = field(default_factory=list)
    unmeasured: int = 0
    notes: list[str] = field(default_factory=list)


def series(frames: dict[str, pd.DataFrame], members_on, breaks=None, stop=None) -> dict[str, Series]:
    days = F.market_days(frames)
    out = {k: Series() for k in F.FACTORS}
    previous = {k: ([], []) for k in F.FACTORS}  # (slice, universe) target names of the previous valid month
    for d in F.formation_days(frames):
        m = F.month(frames, d, {f"{c}.IS" for c in members_on(d)}, days, breaks)
        entry = F.next_session(days, d)
        if not m.valid or entry is None or not m.universe:
            for k in F.FACTORS:
                out[k].unmeasured += 1
            continue
        universe, notes = holding(frames, m.universe, entry, days, stop)
        for k in F.FACTORS:
            s = out[k]
            names = [n for n in m.slices[k] if n in universe]
            if not names:
                s.unmeasured += 1
                continue
            uni = [n for n in m.universe if n in universe]
            gross_s = float(np.mean([universe[n] for n in names]))
            gross_u = float(np.mean([universe[n] for n in uni]))
            old_s, old_u = previous[k]
            net_s, net_u = gross_s - cost(names, old_s), gross_u - cost(uni, old_u)
            high = (gross_s - cost(names, old_s, COST_INFO, COST_INFO)) - (gross_u - cost(uni, old_u, COST_INFO, COST_INFO))
            s.months.append(pd.Timestamp(entry).to_period("M"))
            s.slice_net.append(net_s)
            s.universe_net.append(net_u)
            s.excess.append(net_s - net_u)
            s.excess_high_cost.append(high)
            s.notes += [f"{d}: {n}" for n in notes if n.split()[0] in names]
            previous[k] = (names, uni)
    return out


def block_bootstrap(x: np.ndarray, block: int = BLOCK, draws: int = DRAWS, seed: int = SEED) -> np.ndarray:
    """Means of `draws` moving-block resamples of x (same length)."""

    n = len(x)
    rng = np.random.default_rng(seed)
    count = math.ceil(n / block)
    starts = rng.integers(0, n - block + 1, (draws, count))
    picks = (starts[..., None] + np.arange(block)).reshape(draws, -1)[:, :n]
    return x[picks].mean(axis=1)


@dataclass
class Verdict:
    factor: str
    months: int
    mean: float = math.nan
    lower: float = math.nan
    upper: float = math.nan
    years_positive: int = 0
    lower_risk: bool | None = None
    mean_high_cost: float = math.nan
    label: str = UNMEASURED
    reasons: list[str] = field(default_factory=list)


def judge(factor: str, s: Series, draws: int = DRAWS) -> Verdict:
    v = Verdict(factor=factor, months=len(s.excess))
    if v.months < F.MIN_VALID_MONTHS:
        v.reasons.append(f"geçerli ay {v.months} < {F.MIN_VALID_MONTHS}")
        return v
    x = np.asarray(s.excess, dtype=float)
    means = block_bootstrap(x, draws=draws)
    v.mean = float(x.mean())
    v.lower, v.upper = float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))
    v.mean_high_cost = float(np.mean(s.excess_high_cost))
    by_year = pd.Series(x, index=[p.year for p in s.months]).groupby(level=0).mean()
    v.years_positive = int(sum(by_year.get(y, -1) > 0 for y in YEARS))
    checks = [(v.mean > 0, "ortalama fazla getiri ≤ 0"), (v.lower > 0, "alt sınır ≤ 0"),
              (v.years_positive >= 2, f"2023–2025'te pozitif yıl {v.years_positive} < 2")]
    if factor == "dusuk_oynaklik":
        v.lower_risk = float(np.std(s.slice_net, ddof=1)) < float(np.std(s.universe_net, ddof=1))
        checks.append((v.lower_risk, "dilimin aylık getiri oynaklığı evreninkinden düşük değil"))
    v.reasons = [why for ok, why in checks if not ok]
    if not v.reasons:
        v.label = PASSED
    elif v.upper < LITERATURE:
        v.label = EXCLUDED
    else:
        v.label = UNANSWERED
    return v


def combine(a: Verdict, b: Verdict) -> str:
    """K-78 two downloads: no choosing, no averaging."""

    if UNMEASURED in (a.label, b.label):
        return UNMEASURED
    if a.label == PASSED and b.label == PASSED:
        return PASSED
    if PASSED in (a.label, b.label):
        return SENSITIVE
    return a.label if a.label == b.label else UNANSWERED


def text(verdicts: list[Verdict]) -> str:
    lines = []
    for v in verdicts:
        lines.append(f"{v.factor}: {v.label}; {v.months} ay")
        if not math.isnan(v.mean):
            lines.append(f"  ortalama aylık fazla getiri %{v.mean * 100:.2f}; alt sınır (%97,5) %{v.lower * 100:.2f}; "
                         f"üst uç (%95) %{v.upper * 100:.2f}; pozitif yıl {v.years_positive}/3; "
                         f"bilgi: %0,30 maliyetle ortalama %{v.mean_high_cost * 100:.2f}")
        if v.reasons:
            lines.append("  sağlanmayan: " + "; ".join(v.reasons))
    return "\n".join(lines)


__all__ = ["EXCLUDED", "PASSED", "SENSITIVE", "UNANSWERED", "UNMEASURED", "Series", "Verdict", "block_bootstrap",
           "combine", "cost", "holding", "judge", "series", "text"]
