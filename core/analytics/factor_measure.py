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
from core.market.universe import BENCHMARK

COST_BUY = COST_SELL = 0.0015
COST_INFO = 0.0030          # information line only; never changes the verdict
BLOCK, DRAWS, SEED = 3, 10_000, 0
LITERATURE = 0.005          # monthly; an upper end below it excludes a literature-sized effect
YEARS = (2023, 2024, 2025)

PASSED = "KEŞİFTE GEÇTİ"
EXCLUDED = "GEÇMEDİ (literatür büyüklüğünde bir etki dışlandı)"
UNANSWERED = "YANITLANAMADI (güç yetersiz)"
FAILED_CONDITION = "GEÇMEDİ (alt sınır pozitif, ek koşul sağlanmadı)"
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
    benchmark: list[float] = field(default_factory=list)  # XU100 over the same holding; nan when missing
    no_price: int = 0
    data_break: int = 0
    limit_open: int = 0
    no_entry: int = 0


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
        reasons = list(m.not_applicable.values())
        index = frames.get(BENCHMARK)
        index_return = math.nan
        if index is not None and pd.Timestamp(entry) in index.index:
            index_return = holding({BENCHMARK: index}, [BENCHMARK], entry, days, stop)[0].get(BENCHMARK, math.nan)
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
            s.benchmark.append(index_return)
            s.no_price += m.no_price
            s.data_break += len(m.data_break)
            s.limit_open += reasons.count("tavan açılış")
            s.no_entry += reasons.count("giriş günü veri yok")
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
    elif v.lower > 0:  # the interval is clear of zero: power is not what stopped it
        v.label = FAILED_CONDITION
    elif v.upper < LITERATURE:
        v.label = EXCLUDED
    else:
        v.label = UNANSWERED
    return v


def information(s: Series, cpi: pd.DataFrame | None = None) -> str:
    """The K-78 information lines. They never change a verdict."""

    if cpi is None:
        from core.market.macro import CPI_FILE, load_cpi

        cpi = load_cpi(CPI_FILE)
    net, index = np.asarray(s.slice_net, dtype=float), np.asarray(s.benchmark, dtype=float)
    known = ~np.isnan(index)
    over = f"%{float((net[known] - index[known]).mean()) * 100:.2f} ({int(known.sum())} ay)" if known.any() else "veri yok"
    real = [(1 + r) / (1 + float(cpi.at[str(p), "monthly_pct"]) / 100) - 1
            for p, r in zip(s.months, s.slice_net, strict=True) if str(p) in cpi.index]
    deflated = f"%{float(np.mean(real)) * 100:.2f} ({len(real)} ay)" if real else "veri yok"
    return (f"  bilgi: dilimin XU100'e göre aylık farkı {over}; dilimin aylık reel getirisi {deflated}\n"
            f"  sayımlar: ölçülemeyen ay {s.unmeasured}; fiyatsız üye {s.no_price}; veri kırığı {s.data_break}; "
            f"tavan açılış {s.limit_open}; giriş verisi yok {s.no_entry}; kilitli çıkış {len(s.notes)}")


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


DAILY_A = "56016f5992f458527a3100321379a11a5a6753730e0e1fbc848ce30505508a18"  # frozen daily snapshot (04.11)
MIN_GAP_DAYS = 7
FRESH_B = "Yahoo auto_adjust=True, boş depoya baştan indirildi"  # what the workflow writes into B's manifest
MIN_B_SHARE = 0.95                                               # of A's symbols; fewer means a broken download


def prepare(raw: dict[str, pd.DataFrame], start: pd.Timestamp, actions=None):
    """Both downloads the same way: before HOLDOUT_START, from the common start, K-78 corporate actions."""

    from core.backtest.run import HOLDOUT_START
    from core.market.corrections import load_corporate_actions

    actions = load_corporate_actions() if actions is None else actions
    frames, skipped, breaks = {}, [], {}
    for sym, df in raw.items():
        df = df[(df.index >= start) & (df.index < HOLDOUT_START)]
        if df.empty:
            continue
        frames[sym], out, broken = F.adjust_checked(df, [a for a in actions if a.symbol == sym])
        skipped += out
        if broken:
            breaks[sym] = broken
    return frames, skipped, breaks


def check_pair(first: date, second: date) -> list[str]:
    problems = []
    if (second - first).days < MIN_GAP_DAYS:
        problems.append(f"iki indirme arası {(second - first).days} gün < {MIN_GAP_DAYS}")
    return problems


def check_b(source: str, day: date, raw_a: dict[str, pd.DataFrame], raw_b: dict[str, pd.DataFrame]) -> list[str]:
    """B must be the fresh download K-78 asks for: its manifest says so, it is complete and it ends with A."""

    problems = []
    if FRESH_B not in source:
        problems.append(f"B'nin kaynağı baştan indirme değil ({source or 'kaynak yok'})")
    elif day.isoformat() not in source:
        problems.append(f"--tarih-b {day} B'nin kaynağındaki günle aynı değil")
    if len(raw_b) < MIN_B_SHARE * len(raw_a):
        problems.append(f"B eksik: {len(raw_b)} sembol, A'da {len(raw_a)}")
    last = [max(df.index.max() for df in raw.values() if len(df)) for raw in (raw_a, raw_b) if raw]
    if len(last) == 2 and last[0] != last[1]:
        problems.append(f"son tarihler farklı: A {last[0].date()}, B {last[1].date()}")
    return problems


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys
    from pathlib import Path

    from core.analytics import provenance as P
    from core.infrastructure.console import utf8_output
    from core.market.membership import members_on

    utf8_output()
    parser = argparse.ArgumentParser(description="K-78 keşif ölçümü (iki dondurulmuş günlük görüntü)")
    parser.add_argument("a")
    parser.add_argument("b")
    parser.add_argument("--tarih-a", required=True, help="A'nın indirildiği gün YYYY-AA-GG")
    parser.add_argument("--tarih-b", required=True, help="B'nin indirildiği gün YYYY-AA-GG")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    problems = check_pair(date.fromisoformat(args.tarih_a), date.fromisoformat(args.tarih_b))
    raw_a, raw_b = P.thaw(Path(args.a)), P.thaw(Path(args.b))
    if P.digest(raw_a) != DAILY_A:
        problems.append("A, dondurulmuş günlük görüntü (56016f59…) değil")
    problems += check_b(P.manifest(Path(args.b)).get("source", ""), date.fromisoformat(args.tarih_b), raw_a, raw_b)
    if problems:
        print("K-78 ölçüm koşulu sağlanmadı: " + "; ".join(problems) + ". Durdu.")
        return 2
    start = max(min(df.index.min() for df in raw.values() if len(df)) for raw in (raw_a, raw_b))
    print(f"Kod: {P.code_version().line()}")
    labels = {}
    for name, raw in (("A", raw_a), ("B", raw_b)):
        frames, skipped, breaks = prepare(raw, start)
        print(f"İndirme {name}: {P.stamp(frames)}")
        if skipped:
            print("  uygulanmayan şirket işlemi: " + "; ".join(skipped))
        measured = series(frames, lambda d: members_on(d), breaks)
        verdicts = [judge(k, s) for k, s in measured.items()]
        for v in verdicts:
            print(text([v]))
            print(information(measured[v.factor]))
            for note in measured[v.factor].notes:
                print("  " + note)
        labels[name] = verdicts
    for va, vb in zip(labels["A"], labels["B"], strict=True):
        print(f"SONUÇ {va.factor}: {combine(va, vb)}")
    print("Not: keşif sonucudur; canlı kurala, karta, /saglik'e ya da K-64'e otomatik geçiş yok.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["EXCLUDED", "FAILED_CONDITION", "PASSED", "SENSITIVE", "UNANSWERED", "UNMEASURED", "Series", "Verdict",
           "block_bootstrap", "check_b", "check_pair", "combine", "cost", "holding", "information", "judge", "prepare",
           "series", "text"]
