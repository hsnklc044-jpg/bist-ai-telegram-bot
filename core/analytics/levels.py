"""
QuantBIST
Support and resistance levels (Özellik Talimatı A; DECISIONS K-49). Pure functions on closed,
ADJUSTED daily candles; the caller cuts the candles at the day it wants (or passes `asof`), so a
level never uses a later candle. Every constant is written in K-49 before any result and is
never tuned on results.

A level is information, not advice: "teknik seviye, öneri değil".
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

N = 5  # fractal: sessions on each side
LOOKBACK = 252
CLUSTER_ATR = 0.5
BREAK_ATR = 0.5
LIMIT_MOVE = 0.095  # a close-to-close move beyond ±9.5%: a locked (limit) day makes no pivot
MIN_CANDLES = 2 * N + 15
METHODS = ("küme", "pivot_gün", "pivot_hafta", "52h_zirve", "52h_dip", "psikolojik", "sma50", "sma200")
LABEL = "teknik seviye, öneri değil"


@dataclass(frozen=True)
class Pivot:
    day: pd.Timestamp
    price: float
    kind: str  # "tepe" | "dip"


@dataclass(frozen=True)
class Level:
    price: float
    kind: str  # "destek" (below the last close) | "direnç" (above)
    method: str
    strength: int | None  # 0-100, "küme" levels only
    touches: int
    last_touch: date | None
    breaks: int
    dist_atr: float
    dist_pct: float
    name: str = ""  # P, R1, D1, R2, D2 for the classic pivots


def atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    from core.strategy.score import average_true_range

    return average_true_range(df["high"], df["low"], df["close"], window)


def pivots(df: pd.DataFrame, n: int = N) -> list[Pivot]:
    """Confirmed fractal tops and bottoms: t is a top if high[t] > max(high[t-n..t-1]) and
    high[t] >= max(high[t+1..t+n]); it exists only once t+n has closed. Limit days are skipped."""

    high, low, close = (df[c].to_numpy(dtype=float) for c in ("high", "low", "close"))
    move = np.abs(close / np.r_[np.nan, close[:-1]] - 1)
    out = []
    for t in range(n, len(df) - n):
        if move[t] > LIMIT_MOVE:
            continue
        if high[t] > high[t - n:t].max() and high[t] >= high[t + 1:t + n + 1].max():
            out.append(Pivot(df.index[t], float(high[t]), "tepe"))
        if low[t] < low[t - n:t].min() and low[t] <= low[t + 1:t + n + 1].min():
            out.append(Pivot(df.index[t], float(low[t]), "dip"))
    return out


def cluster(points: list[Pivot], width: float) -> list[list[Pivot]]:
    """Sorted by price; a point closer than `width` to the previous one joins its group."""

    groups: list[list[Pivot]] = []
    for p in sorted(points, key=lambda p: (p.price, p.day)):
        if groups and p.price - groups[-1][-1].price < width:
            groups[-1].append(p)
        else:
            groups.append([p])
    return groups


def count_breaks(close: pd.Series, level: float, atr_series: pd.Series) -> int:
    """How many times the close went to the other side of `level` by more than BREAK_ATR x ATR
    (a new break needs a move back across first)."""

    return _breaks(close.to_numpy(dtype=float), atr_series.reindex(close.index).to_numpy(dtype=float), level)


def _breaks(close: np.ndarray, atr_values: np.ndarray, level: float) -> int:
    with np.errstate(invalid="ignore"):
        side = np.where(close > level + BREAK_ATR * atr_values, 1, np.where(close < level - BREAK_ATR * atr_values, -1, 0))
    side = side[side != 0]
    return int(np.count_nonzero(side[1:] != side[:-1])) if len(side) > 1 else 0


def classic(high: float, low: float, close: float) -> dict[str, float]:
    p = (high + low + close) / 3
    return {"P": p, "R1": 2 * p - low, "D1": 2 * p - high, "R2": p + (high - low), "D2": p - (high - low)}


def round_numbers(price: float) -> tuple[float, float]:
    """The round numbers on each side: step 10^floor(log10(price)) / 2 (270 -> 250 and 300)."""

    step = 10 ** math.floor(math.log10(price)) / 2
    below = math.floor(price / step + 1e-9) * step
    return round(below, 10), round(below + step, 10)


def strength(touches: int, age: int, breaks: int) -> int:
    return round(100 * (1 - math.exp(-touches / 2)) * math.exp(-age / LOOKBACK) * 0.5 ** breaks)


def levels(df: pd.DataFrame, asof=None) -> list[Level]:
    """Every level known at the close of `asof` (default: the last candle), nearest first."""

    if asof is not None:
        df = df.loc[:pd.Timestamp(asof)]
    if len(df) < MIN_CANDLES:
        return []
    window = df.iloc[-LOOKBACK:]
    a = atr(df)
    last_atr, last = float(a.iloc[-1]), float(df["close"].iloc[-1])
    if not last_atr == last_atr or last_atr <= 0:
        return []
    found: list[tuple] = []

    for group in cluster(pivots(window), CLUSTER_ATR * last_atr):
        price = float(np.mean([p.price for p in group]))
        first, latest = min(p.day for p in group), max(p.day for p in group)
        breaks = count_breaks(window["close"].loc[first:], price, a)
        age = int(len(window.loc[latest:]) - 1)
        found.append((price, "küme", strength(len(group), age, breaks), len(group), latest.date(), breaks, ""))

    day = df.iloc[-1]
    for name, value in classic(float(day["high"]), float(day["low"]), float(day["close"])).items():
        found.append((value, "pivot_gün", None, 0, None, 0, name))
    week = df.index.to_period("W")
    previous = df[week < week[-1]]
    if len(previous):
        last_week = previous[previous.index.to_period("W") == previous.index.to_period("W")[-1]]
        for name, value in classic(float(last_week["high"].max()), float(last_week["low"].min()),
                                   float(last_week["close"].iloc[-1])).items():
            found.append((value, "pivot_hafta", None, 0, None, 0, name))
    found.append((float(window["high"].max()), "52h_zirve", None, 0, None, 0, ""))
    found.append((float(window["low"].min()), "52h_dip", None, 0, None, 0, ""))
    for value in round_numbers(last):
        found.append((value, "psikolojik", None, 0, None, 0, ""))
    for n, name in ((50, "sma50"), (200, "sma200")):
        if len(df) >= n:
            found.append((float(df["close"].iloc[-n:].mean()), name, None, 0, None, 0, ""))

    out = [Level(price, "destek" if price < last else "direnç", method, power, touches, touched, breaks,
                 (price - last) / last_atr, (price / last - 1) * 100, name)
           for price, method, power, touches, touched, breaks, name in found if price != last]
    return sorted(out, key=lambda lv: abs(lv.dist_atr))


SERIES = ("destek_uzaklik_atr", "direnc_uzaklik_atr", "seviye_gucu", "kirdi_yukari", "kirdi_asagi")


def daily_series(df: pd.DataFrame, recent: int | None = None) -> pd.DataFrame:
    """The /tara fields on every day, each equal to levels() on the candles cut at that day:
    the nearest cluster support and resistance (ATR distance), the nearest cluster's strength,
    and kirdi_yukari / kirdi_asagi (1: the close passed yesterday's nearest resistance / support
    by more than BREAK_ATR x today's ATR; 0: not; NaN: no level known). `recent`: only the last
    `recent` days are computed (the live list looks back ≤ 62 sessions), the rest stay NaN."""

    n, out = len(df), pd.DataFrame(np.nan, index=df.index, columns=list(SERIES))
    if n < MIN_CANDLES:
        return out
    high, low, close = (df[c].to_numpy(dtype=float) for c in ("high", "low", "close"))
    a = atr(df).to_numpy(dtype=float)
    move = np.abs(close / np.r_[np.nan, close[:-1]] - 1)
    hs, ls = pd.Series(high), pd.Series(low)
    left_max, left_min = hs.rolling(N).max().shift(1).to_numpy(), ls.rolling(N).min().shift(1).to_numpy()
    right_max = hs[::-1].rolling(N).max().shift(1)[::-1].to_numpy()
    right_min = ls[::-1].rolling(N).min().shift(1)[::-1].to_numpy()
    ok = ~(move > LIMIT_MOVE)
    with np.errstate(invalid="ignore"):
        top = ok & (high > left_max) & (high >= right_max)
        bottom = ok & (low < left_min) & (low <= right_min)
    points = sorted([(t, high[t]) for t in np.flatnonzero(top)] + [(t, low[t]) for t in np.flatnonzero(bottom)])
    times = np.array([p[0] for p in points], dtype=int)
    prices = np.array([p[1] for p in points], dtype=float)
    columns = {c: np.full(n, np.nan) for c in SERIES}
    previous = (np.nan, np.nan)  # yesterday's nearest support and resistance prices
    first_day = MIN_CANDLES - 1 if recent is None else max(MIN_CANDLES - 1, n - recent - 1)
    for d in range(first_day, n):
        width, last = CLUSTER_ATR * a[d], close[d]
        if not width == width or width <= 0:
            previous = (np.nan, np.nan)
            continue
        start = max(0, d - LOOKBACK + 1)
        pick = (times >= start + N) & (times <= d - N)
        t_now, p_now = times[pick], prices[pick]
        support = resistance = np.nan
        if len(p_now):
            order = np.lexsort((t_now, p_now))
            t_now, p_now = t_now[order], p_now[order]
            group = np.r_[0, np.cumsum(np.diff(p_now) >= width)]
            best, best_dist = None, np.inf
            for g in range(group[-1] + 1):
                members = group == g
                price = float(np.mean(p_now[members]))
                if price == last:
                    continue
                if price < last and not price <= support:
                    support = price
                if price > last and not price >= resistance:
                    resistance = price
                dist = abs(price - last) / a[d]
                if dist < best_dist:
                    best, best_dist = (price, t_now[members]), dist
            if best is not None:
                price, ts = best
                first, latest = int(ts.min()), int(ts.max())
                breaks = _breaks(close[first:d + 1], a[first:d + 1], price)
                columns["seviye_gucu"][d] = strength(int(len(ts)), d - latest, breaks)
        columns["destek_uzaklik_atr"][d] = (support - last) / a[d]
        columns["direnc_uzaklik_atr"][d] = (resistance - last) / a[d]
        if len(p_now):
            prev_support, prev_resistance = previous
            columns["kirdi_yukari"][d] = float(prev_resistance == prev_resistance and last > prev_resistance + BREAK_ATR * a[d])
            columns["kirdi_asagi"][d] = float(prev_support == prev_support and last < prev_support - BREAK_ATR * a[d])
        previous = (support, resistance)
    if recent is not None and first_day > MIN_CANDLES - 1:  # the extra day only gave yesterday's levels
        for c in SERIES:
            columns[c][first_day] = np.nan
    return pd.DataFrame(columns, index=df.index)


LOG_COLUMNS = ("day", "symbol", "method", "price", "kind", "strength", "touches", "breaks", "logged_at")


def _log_file():
    from core.config.paths import LOG_DIR

    return LOG_DIR / "levels_log.csv"


def last_log_day(path=None) -> date | None:
    from pathlib import Path

    path = Path(path or _log_file())
    if not path.exists():
        return None
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    return date.fromisoformat(lines[-1].split(",", 1)[0]) if len(lines) > 1 else None


def write_log(day: date, frames: dict[str, pd.DataFrame], path=None, now=None) -> int:
    """The cluster levels of `day` for every stock, written after the report and before the
    outcome is known (Özellik A §3.4). Append-only; a day is written once."""

    import csv
    from pathlib import Path

    from core.infrastructure.csvfiles import open_append
    from core.market.calendar import now_istanbul

    path = Path(path or _log_file())
    last = last_log_day(path)
    if last is not None and last >= day:
        return 0
    stamp = (now or now_istanbul()).isoformat(timespec="seconds")
    rows = []
    for symbol, df in sorted(frames.items()):
        cut = df.loc[:pd.Timestamp(day)]
        if cut.empty or cut.index[-1].date() != day:
            continue
        rows += [(day.isoformat(), symbol.removesuffix(".IS"), lv.method, f"{lv.price:.4f}", lv.kind, lv.strength,
                  lv.touches, lv.breaks, stamp) for lv in levels(cut) if lv.method == "küme"]
    if rows:
        path.parent.mkdir(parents=True, exist_ok=True)
        fh, new_file = open_append(path)
        with fh:
            writer = csv.writer(fh, lineterminator="\n")
            if new_file:
                writer.writerow(LOG_COLUMNS)
            writer.writerows(rows)
    return len(rows)


def position_line(df: pd.DataFrame) -> str:
    """The daily report's information line under a position: the nearest cluster support."""

    from core.reports.daily import tr

    supports = [lv for lv in levels(df) if lv.method == "küme" and lv.kind == "destek"]
    if not supports:
        return ""
    lv = max(supports, key=lambda lv: lv.price)
    distance = f"{lv.dist_atr:+.1f}".replace(".", ",")
    return f"     en yakın destek {tr(lv.price, 2)} (küme, güç {lv.strength}, {distance} ATR) – {LABEL}"


def nearest(found: list[Level], k: int = 3) -> dict[str, list[Level]]:
    supports = sorted((lv for lv in found if lv.kind == "destek"), key=lambda lv: -lv.price)[:k]
    resistances = sorted((lv for lv in found if lv.kind == "direnç"), key=lambda lv: lv.price)[:k]
    return {"destek": supports, "direnç": resistances}


def _line(lv: Level) -> str:
    from core.reports.daily import tr

    power = f" · güç {lv.strength} ({lv.touches} dokunma, {lv.breaks} kırılma)" if lv.strength is not None else ""
    atr_text = f"{lv.dist_atr:+.1f}".replace(".", ",")
    pct_text = f"{'+' if lv.dist_pct >= 0 else '−'}%{abs(lv.dist_pct):.1f}".replace(".", ",")
    method = f"{lv.method} {lv.name}" if lv.name else lv.method
    return f"  {tr(lv.price, 2)} · {method} · {atr_text} ATR ({pct_text}){power}"


def levels_text(symbol: str, df: pd.DataFrame, day: date | None = None, k: int | None = None) -> str:
    """/seviye (every level) or the /analyze block (k nearest on each side)."""

    found = levels(df)
    code = symbol.removesuffix(".IS")
    if not found:
        return f"{code}: seviye hesaplanamadı (en az {MIN_CANDLES} kapanmış mum gerekir). {LABEL}."
    shown = nearest(found, k or len(found))
    when = f" ({day:%d.%m.%Y} kapanışı)" if day else ""
    lines = [f"📐 {code} seviyeleri{when} – {LABEL}"]
    for kind, title in (("direnç", "Direnç (yakından uzağa):"), ("destek", "Destek (yakından uzağa):")):
        lines += [title, *([_line(lv) for lv in shown[kind]] or ["  —"])]
    lines.append("Yöntemler: küme = salınım tepe/diplerinin 0,5 ATR kümesi; pivot = klasik (önceki gün/hafta); "
                 "52h = 52 hafta; psikolojik = yuvarlak sayı; sma = basit ortalama. Uzaklık ATR ve yüzde.")
    return "\n".join(lines)


__all__ = ["LABEL", "Level", "METHODS", "Pivot", "SERIES", "atr", "classic", "cluster", "count_breaks", "daily_series",
           "last_log_day", "levels", "position_line", "write_log",
           "levels_text", "nearest", "pivots", "round_numbers", "strength"]
