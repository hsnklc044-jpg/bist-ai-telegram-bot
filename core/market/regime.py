"""
QuantBIST
Market regime and sector context (Talimat C §C1.3, §C2.3; DECISIONS K-51). The definition was
fixed before any result was seen and its thresholds are never tuned on results.

Every day uses only data up to its own close:
- trend:      XU100 close above or below its 200-session simple average;
- volatility: the 20-session standard deviation of XU100's daily log returns, as a percentile of
              the PREVIOUS 252 sessions' values (≥ 80: "yüksek oynaklık");
- breadth:    share of that day's BIST 100 members (point-in-time) closing above their own EMA50.

Label: "yüksek oynaklık" first; then "yükseliş" (above, breadth ≥ 50%), "düşüş" (below,
breadth < 50%), otherwise "karışık"; "bilinmiyor" when any input is missing (200 sessions, the
252-session window, or fewer than 20 members with an EMA50).

The regime is a label, not a signal. The research report's 63-session regime
(core.backtest.reliability.market_regime) is a different, older definition and stays separate.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

TREND_WINDOW = 200
VOL_WINDOW = 20
VOL_HISTORY = 252
VOL_HIGH = 80.0
EMA_SPAN = 50
BREADTH_LINE = 0.50
MIN_MEMBERS = 20
LABELS = ("yükseliş", "düşüş", "karışık", "yüksek oynaklık", "bilinmiyor")
# Borsa İstanbul's four main sector indices; prices from the same source as every other price
SECTORS = {"XBANK.IS": "Banka", "XUSIN.IS": "Sınai", "XUHIZ.IS": "Hizmetler", "XHOLD.IS": "Holding ve Yatırım"}
HORIZONS = (1, 5, 20)
NOTE = "Rejim bir etikettir, sinyal değildir; tanımı sonuç görülmeden sabitlendi (K-51)."
DISCLAIMER = "Kural çıktısıdır, öneri değildir. Karar ve sorumluluk kullanıcıdadır."


def label(trend: str | None, vol_pct: float | None, breadth: float | None) -> str:
    if trend is None or vol_pct is None or breadth is None:
        return "bilinmiyor"
    if any(isinstance(x, float) and np.isnan(x) for x in (vol_pct, breadth)):
        return "bilinmiyor"
    if vol_pct >= VOL_HIGH:
        return "yüksek oynaklık"
    if trend == "üstünde" and breadth >= BREADTH_LINE:
        return "yükseliş"
    if trend == "altında" and breadth < BREADTH_LINE:
        return "düşüş"
    return "karışık"


def _percentile_of_previous(values: pd.Series, window: int) -> pd.Series:
    """For each day: share (×100) of the previous `window` values that are ≤ today's value."""

    arr = values.to_numpy(dtype=float)
    out = np.full(len(arr), np.nan)
    for t in range(window, len(arr)):
        prior = arr[t - window:t]
        if np.isnan(arr[t]) or np.isnan(prior).any():
            continue
        out[t] = (prior <= arr[t]).mean() * 100
    return pd.Series(out, index=values.index)


def components(bench_close: pd.Series, frames: dict, eligible: pd.DataFrame | None) -> pd.DataFrame:
    """Per XU100 session: sma200, trend, vol20, vol_pct, breadth, members."""

    close = bench_close.astype(float)
    out = pd.DataFrame(index=close.index)
    out["sma200"] = close.rolling(TREND_WINDOW).mean()
    out["trend"] = np.where(out["sma200"].isna(), None, np.where(close > out["sma200"], "üstünde", "altında"))
    out["vol20"] = np.log(close).diff().rolling(VOL_WINDOW).std()
    out["vol_pct"] = _percentile_of_previous(out["vol20"], VOL_HISTORY)

    if frames:
        closes = pd.DataFrame({s: df["close"] for s, df in frames.items()}).reindex(close.index)
        counts = closes.notna().cumsum()
        ema = closes.ewm(span=EMA_SPAN, adjust=False).mean().where(counts >= EMA_SPAN)
        valid = ema.notna() & closes.notna()
        if eligible is not None:
            valid &= eligible.reindex(index=close.index, columns=closes.columns).fillna(False).astype(bool)
        above = (closes > ema) & valid
        members = valid.sum(axis=1)
        out["breadth"] = (above.sum(axis=1) / members.where(members > 0)).where(members >= MIN_MEMBERS)
        out["members"] = members
    else:
        out["breadth"] = np.nan
        out["members"] = 0
    return out


def labels(bench_close: pd.Series, frames: dict, eligible: pd.DataFrame | None) -> pd.Series:
    parts = components(bench_close, frames, eligible)
    return pd.Series([label(t, v, b) for t, v, b in zip(parts["trend"], parts["vol_pct"], parts["breadth"],
                                                         strict=True)], index=parts.index, dtype=object)


def relative_strength(sector_close: pd.Series, bench_close: pd.Series, n: int) -> float | None:
    """Sector return minus XU100 return over the last n sessions, in percentage points."""

    both = pd.concat([sector_close, bench_close], axis=1, join="inner").dropna()
    if len(both) <= n:
        return None
    a, b = both.iloc[-1 - n], both.iloc[-1]
    return float((b.iloc[0] / a.iloc[0] - 1) * 100 - (b.iloc[1] / a.iloc[1] - 1) * 100)


def _points(x: float | None) -> str:
    if x is None:
        return "—"
    return f"{'+' if x >= 0 else '−'}{abs(x):.1f}".replace(".", ",")


def market_text(bench: pd.DataFrame, frames: dict, sectors: dict, day: date | None = None,
                eligible: pd.DataFrame | None = None) -> str:
    """/piyasa: the regime with its three inputs, breadth, and the four main sectors against XU100."""

    if bench is None or bench.empty:
        return "\n".join(["🌐 Piyasa", "Rejim: bilinmiyor (XU100 verisi yok)", "", NOTE, DISCLAIMER])
    parts = components(bench["close"], frames, eligible)
    last = parts.iloc[-1]
    day = day or bench.index[-1].date()
    name = label(last["trend"], last["vol_pct"], last["breadth"])

    if last["trend"] is None:
        trend = "200 seans geçmiş yok"
    else:
        gap = (bench["close"].iloc[-1] / last["sma200"] - 1) * 100
        trend = f"XU100 200 günlük ortalamanın %{abs(gap):.1f} {'üstünde' if gap >= 0 else 'altında'}".replace(".", ",")
    vol = "yüzdelik yok" if np.isnan(last["vol_pct"]) else f"oynaklık yüzdeliği {last['vol_pct']:.0f}"
    if np.isnan(last["breadth"]):
        breadth = f"bilinmiyor ({int(last['members'])} hissede EMA50 var; en az {MIN_MEMBERS} gerekir)"
    else:
        breadth = f"BIST 100'ün %{last['breadth'] * 100:.0f}'ı EMA50 üstünde ({int(last['members'])} hisse)"

    lines = [f"🌐 Piyasa – {day:%d.%m.%Y} kapanışı",
             f"Rejim: {name} ({trend}; {vol})",
             f"Genişlik: {breadth}",
             f"Sektörler XU100'e göre ({' / '.join(str(h) for h in HORIZONS)} seans, puan):"]
    for symbol, title in SECTORS.items():
        df = sectors.get(symbol)
        if df is None or df.empty:
            lines.append(f"  {title}: veri yok")
            continue
        values = [_points(relative_strength(df["close"], bench["close"], n)) for n in HORIZONS]
        lines.append(f"  {title}: {' / '.join(values)}")
    lines += ["", NOTE, DISCLAIMER]
    return "\n".join(lines)


def live_text(day: date | None = None) -> str:
    """/piyasa from the price store: today's BIST 100 members, XU100 and the sector indices."""

    from core.market.universe import BENCHMARK
    from core.reports.daily import adjusted_bars
    from core.screen.universe import symbols

    members = symbols("bist100", today=day)
    frames = {s: df for s in members if not (df := adjusted_bars(s)).empty}
    sectors = {s: adjusted_bars(s) for s in SECTORS}
    return market_text(adjusted_bars(BENCHMARK), frames, sectors, day=day)


__all__ = ["DISCLAIMER", "LABELS", "NOTE", "SECTORS", "components", "label", "labels", "live_text", "market_text",
           "relative_strength"]
