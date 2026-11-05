"""
QuantBIST
K-78 long-horizon price factors: the parts fixed before any measurement (DECISIONS K-78, 05.11.2026).

This module holds only what the pre-tests check: the K-78 double-adjustment guard, the factor values,
the monthly universe (BIST 100 members on the day, liquidity cut, 252-session history), the slice,
the applicability rules applied to the slice and the universe alike, and the coverage counts. It
computes no return and runs no measurement; the measurement is a later, separate step.

    python -m core.analytics.factor_study kapsam GUNLUK_GORUNTU_KLASORU
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd

MOMENTUM_FROM, MOMENTUM_TO = 252, 21  # return from the close t-252 to the close t-21
VOL_WINDOW = 252                      # daily log returns of the last 252 sessions
HISTORY = 253                         # closes needed for either factor
LIQ_WINDOW, LIQ_SHARE = 20, 0.20      # bottom 20% by the 20-session median TL turnover leave
MIN_STOCKS, MIN_DATA_MEMBERS = 60, 80  # a month is valid with at least these
MIN_VALID_MONTHS = 36
FIRST_FORMATION, LAST_FORMATION = date(2022, 4, 29), date(2026, 9, 30)
JUMP_TOLERANCE = 0.10                 # the raw ex-date jump must be within ±10% of the recorded factor


# --- data ---------------------------------------------------------------------------------------------


def adjust(raw: pd.DataFrame, actions) -> tuple[pd.DataFrame, list[str]]:
    """
    The K-78 guard: a recorded corporate action is applied only when the raw data shows its jump on the
    ex-date (open / previous close within ±10% of the factor). No jump means the provider has adjusted
    already, or the same action was applied a line earlier: it is not applied (never twice) and is listed.
    """

    df, skipped = raw.copy(), []
    for a in actions:
        factor = a.resolve(raw)
        ex = pd.Timestamp(a.ex_date)
        before, after = df.loc[df.index < ex, "close"], df.loc[df.index >= ex, "open"]  # as adjusted so far
        if not factor or before.empty or after.empty or not before.iloc[-1]:
            skipped.append(f"{a.symbol} {a.ex_date}: veri yok ya da faktör çözülemedi")
            continue
        gap = float(after.iloc[0]) / float(before.iloc[-1])
        if abs(gap / factor - 1) > JUMP_TOLERANCE:
            skipped.append(f"{a.symbol} {a.ex_date}: ham veride sıçrama yok (oran {gap:.3f}, faktör {factor:.3f})")
            continue
        mask = df.index < ex
        df.loc[mask, ["open", "high", "low", "close"]] *= factor
        df.loc[mask, "volume"] /= factor
    return df, skipped


def momentum(close: pd.Series) -> float:
    c = close.dropna()
    if len(c) < HISTORY:
        return math.nan
    return float(c.iloc[-1 - MOMENTUM_TO] / c.iloc[-1 - MOMENTUM_FROM] - 1)


def volatility(close: pd.Series) -> float:
    c = close.dropna()
    if len(c) < HISTORY:
        return math.nan
    return float(np.log(c.iloc[-HISTORY:]).diff().dropna().std(ddof=1))


FACTORS = {"momentum": (momentum, False), "dusuk_oynaklik": (volatility, True)}  # (value, low is chosen)


# --- the month ------------------------------------------------------------------------------------------


def liquidity_cut(frames: dict[str, pd.DataFrame], day: pd.Timestamp, names) -> set[str]:
    """The bottom LIQ_SHARE of `names` by the 20-session median TL turnover up to `day` (ties by code)."""

    turnover = {}
    for s in names:
        df = frames[s].loc[:day]
        if len(df) >= LIQ_WINDOW:
            turnover[s] = float((df["close"] * df["volume"]).tail(LIQ_WINDOW).median())
    if not turnover:
        return set()
    ranked = pd.Series(turnover).sort_index().sort_values(kind="stable")
    return set(ranked.index[: int(len(ranked) * LIQ_SHARE)])


def chosen(values: dict[str, float], low: bool) -> list[str]:
    """floor(n/3) names with the highest (or lowest) value; ties by code."""

    order = sorted(values, key=lambda s: ((values[s] if low else -values[s]), s))
    return order[: len(order) // 3]


def market_days(frames: dict[str, pd.DataFrame]) -> pd.DatetimeIndex:
    """Days on which any stock has a candle (the holiday file starts in 2026, so the data decides)."""

    return pd.DatetimeIndex(sorted(set().union(*(df.index for df in frames.values()))))


def next_session(days: pd.DatetimeIndex, day: date) -> date | None:
    """The first market day after `day`; a day no stock traded is a holiday, not missing data."""

    later = days[days > pd.Timestamp(day)]
    return later[0].date() if len(later) else None


def entry_problem(df: pd.DataFrame, entry: date) -> str | None:
    """Why a position cannot be opened at the entry open: no data that day, or an open at the upper limit."""

    from core.market.limits import limit_up

    ts = pd.Timestamp(entry)
    if ts not in df.index:
        return "giriş günü veri yok"
    prev = df.loc[df.index < ts, "close"]
    if prev.empty:
        return "giriş günü veri yok"
    if limit_up(float(df.at[ts, "open"]) / float(prev.iloc[-1]) - 1):
        return "tavan açılış"
    return None


def exit_close(df: pd.DataFrame, entry: date, last: date) -> tuple[date, float] | None:
    """The close the holding ends on: `last`, or the last close before it when the stock stopped trading."""

    part = df.loc[(df.index >= pd.Timestamp(entry)) & (df.index <= pd.Timestamp(last)), "close"].dropna()
    if part.empty:
        return None
    return part.index[-1].date(), float(part.iloc[-1])


@dataclass
class Month:
    formation: date
    members: int = 0
    no_price: int = 0
    usable: int = 0
    liquidity_out: int = 0
    universe: list[str] = field(default_factory=list)
    slices: dict[str, list[str]] = field(default_factory=dict)
    not_applicable: dict[str, str] = field(default_factory=dict)
    valid: bool = False


def month(frames: dict[str, pd.DataFrame], formation: date, members: set[str], days=None) -> Month:
    """The universe and both slices on one formation day; the same applicability rule on all of them."""

    day = pd.Timestamp(formation)
    m = Month(formation=formation, members=len(members))
    priced = {s for s in members if s in frames and len(frames[s].loc[:day])}
    m.no_price = len(members) - len(priced)
    values = {}
    for s in sorted(priced):
        close = frames[s].loc[:day, "close"]
        row = {k: f(close) for k, (f, _) in FACTORS.items()}
        if all(not math.isnan(v) for v in row.values()):
            values[s] = row
    m.usable = len(values)
    cut = liquidity_cut(frames, day, sorted(priced))
    m.liquidity_out = len(cut & set(values))
    ranked = [s for s in sorted(values) if s not in cut]
    entry = next_session(market_days(frames) if days is None else days, formation)
    for s in ranked:
        problem = entry_problem(frames[s], entry) if entry else "giriş günü veri yok"
        if problem:
            m.not_applicable[s] = problem
    m.universe = [s for s in ranked if s not in m.not_applicable]
    for k, (_, low) in FACTORS.items():
        picked = chosen({s: values[s][k] for s in ranked}, low)
        m.slices[k] = [s for s in picked if s not in m.not_applicable]
    m.valid = len(ranked) >= MIN_STOCKS and m.usable >= MIN_DATA_MEMBERS
    return m


def formation_days(frames: dict[str, pd.DataFrame]) -> list[date]:
    """The last session of every month with data, from FIRST_FORMATION to LAST_FORMATION."""

    idx = market_days(frames)
    ends = pd.Series(idx, index=idx).groupby(idx.to_period("M")).max()
    return [d.date() for d in ends if FIRST_FORMATION <= d.date() <= LAST_FORMATION]


def coverage(frames: dict[str, pd.DataFrame], members_on=None) -> pd.DataFrame:
    """Per formation day, counts only (no factor value, no return)."""

    from core.market.membership import members_on as default

    members_on = members_on or default
    rows, days = [], market_days(frames)
    for d in formation_days(frames):
        m = month(frames, d, {f"{c}.IS" for c in members_on(d)}, days)
        reasons = pd.Series(m.not_applicable, dtype=str)
        rows.append({"formasyon": d, "uye": m.members, "fiyatsiz": m.no_price, "kullanilabilir": m.usable,
                     "likidite_disi": m.liquidity_out, "tavan_acilis": int((reasons == "tavan açılış").sum()),
                     "giris_verisi_yok": int((reasons == "giriş günü veri yok").sum()), "evren": len(m.universe),
                     **{f"dilim_{k}": len(v) for k, v in m.slices.items()}, "gecerli": m.valid})
    return pd.DataFrame(rows)


def main(argv: list[str] | None = None) -> int:
    import sys
    from pathlib import Path

    from core.analytics import provenance as P
    from core.backtest.run import HOLDOUT_START
    from core.infrastructure.console import utf8_output
    from core.market.corrections import load_corporate_actions

    utf8_output()
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 2 or argv[0] != "kapsam":
        print(__doc__)
        return 2
    raw = {s: df[df.index < HOLDOUT_START] for s, df in P.thaw(Path(argv[1])).items()}
    print(P.stamp(raw))
    actions = load_corporate_actions()
    frames, skipped = {}, []
    for s, df in raw.items():
        frames[s], out = adjust(df, [a for a in actions if a.symbol == s])
        skipped += out
    table = coverage(frames)
    print(table.to_string(index=False))
    print(f"Geçerli ay: {int(table['gecerli'].sum())} / {len(table)} (en az {MIN_VALID_MONTHS} gerekir)")
    print("Uygulanmayan şirket işlemi kaydı: " + (str(len(skipped)) if skipped else "yok"))
    for line in skipped:
        print("  " + line)
    print("Not: yalnız kapsam sayısı; faktör değeri ve getiri gösterilmedi, K-78 ölçümü yapılmadı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["FACTORS", "Month", "adjust", "chosen", "coverage", "entry_problem", "exit_close",
           "formation_days", "liquidity_cut", "market_days", "momentum", "month", "next_session", "volatility"]
