"""
QuantBIST
Weekly portfolio health report (road plan, part 2, first item; 05.11.2026).

What the user's own portfolio looks like, measured, without advice:
- distribution: each holding's weight; the largest one; the effective number of holdings
  (1 / sum of squared weights: four equal holdings make 4, one big and three tiny make ~1);
- co-movement: the average pairwise correlation of daily returns over the last CORR_DAYS sessions;
- return: over the last 4 weeks and since the first record, from data/equity_log.csv with money
  moved in or out left out (core.reports.daily.performance_index, Modified Dietz). Commissions are
  in it (the ledger's amounts are after fees); taxes are not. Shown nominal, real (TÜİK CPI as
  published by that day) and in dollars (CBRT USD/TRY), and against BIST 100 over the same days.
A figure that cannot be measured (no CPI month yet, no rate, too few records) is written as
"ölçülemedi" with the reason, never estimated.

    /saglik            the bot command; the bot also sends it every Saturday morning
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd

CORR_DAYS = 60
MIN_CORR_DAYS = 20
WINDOW_DAYS = 28  # "son 4 hafta"
DISCLAIMER = "Ölçüm özetidir, öneri değildir. Karar ve sorumluluk kullanıcıdadır."
ACCOUNT_NAMES = {"real": "Gerçek hesap", "paper": "Sanal hesap"}


@dataclass
class Period:
    label: str
    start: date | None = None
    end: date | None = None
    nominal: float | None = None
    real: float | None = None
    usd: float | None = None
    bench: float | None = None
    why: str = ""  # when nominal is None


@dataclass
class Health:
    account: str
    day: date
    total: float = 0.0
    weights: dict[str, float] = field(default_factory=dict)
    unpriced: list[str] = field(default_factory=list)
    effective: float | None = None
    corr: float | None = None
    corr_days: int = 0
    periods: list[Period] = field(default_factory=list)


def concentration(weights: dict[str, float]) -> float | None:
    """The effective number of holdings, 1 / Σw² (weights of the invested part)."""

    w = np.array([v for v in weights.values() if v > 0], dtype=float)
    if not len(w):
        return None
    w = w / w.sum()
    return float(1 / (w ** 2).sum())


def average_correlation(frames: dict[str, pd.DataFrame], days: int = CORR_DAYS) -> tuple[float | None, int]:
    """Mean of the pairwise correlations of daily close-to-close returns over the last `days` common sessions."""

    if len(frames) < 2:
        return None, 0
    returns = pd.concat({s: df["close"].astype(float).pct_change() for s, df in frames.items() if len(df)},
                        axis=1, sort=True).dropna().tail(days)
    if returns.shape[1] < 2 or len(returns) < MIN_CORR_DAYS:
        return None, len(returns)
    corr = returns.corr().to_numpy()
    upper = corr[np.triu_indices_from(corr, k=1)]
    upper = upper[np.isfinite(upper)]
    return (float(upper.mean()) if len(upper) else None), len(returns)


def period(label: str, index: pd.Series, start: pd.Timestamp, end: pd.Timestamp, bench: pd.Series,
           cpi: pd.DataFrame | None, rates: pd.Series | None) -> Period:
    """One window of the performance index: the last record on or before `start` to the one at `end`."""

    from core.market import macro

    out = Period(label)
    before = index.loc[:start]
    if before.empty or len(index.loc[:end]) < 2:
        out.why = "yeterli değer kaydı yok"
        return out
    a_day, b_day = before.index[-1], index.loc[:end].index[-1]
    if b_day <= a_day:
        out.why = "yeterli değer kaydı yok"
        return out
    out.start, out.end = a_day.date(), b_day.date()
    out.nominal = float(index.loc[b_day] / index.loc[a_day] - 1)
    if cpi is not None and len(cpi):
        out.real = macro.real_return(out.nominal, out.start, out.end, cpi)
    if rates is not None and len(rates):
        out.usd = macro.usd_return(out.nominal, out.start, out.end, rates)
    b = bench.loc[:b_day]
    a = bench.loc[:a_day]
    if len(a) and len(b):
        out.bench = float(b.iloc[-1] / a.iloc[-1] - 1)
    return out


def build(account: str = "real", day: date | None = None, entries=None, equity: pd.Series | None = None,
          bars=None, bench: pd.Series | None = None, cpi: pd.DataFrame | None = None,
          rates: pd.Series | None = None, price_bars=None) -> Health:
    """`price_bars`: the last raw close values a holding (as /portfolio does); `bars`: adjusted candles
    for the correlation."""
    from core.reports.daily import performance_index, value_holdings

    day = day or date.today()
    if entries is None:
        from core.ledger.book import load_ledger

        entries = load_ledger()
    health = Health(account, day)
    holdings, invested = value_holdings(entries, account, price_bars)
    values = {h.position.symbol: h.value for h in holdings}
    health.unpriced = sorted(s for s, v in values.items() if v is None or pd.isna(v))
    priced = {s: v for s, v in values.items() if s not in health.unpriced}
    health.total = float(invested)
    if account == "paper":
        from core.ledger.book import cash_balance

        health.total += cash_balance(entries, "paper")
    if health.total > 0:
        health.weights = dict(sorted(((s, v / health.total) for s, v in priced.items()), key=lambda kv: -kv[1]))
    health.effective = concentration(priced)
    if bars is None:
        from core.reports.daily import adjusted_bars as bars
    health.corr, health.corr_days = average_correlation({s: bars(s) for s in priced})
    if equity is not None and len(equity) >= 2:
        index = performance_index(equity, entries, account)
        end = pd.Timestamp(day)
        bench = bench if bench is not None else pd.Series(dtype=float)
        health.periods = [period("Son 4 hafta", index, end - pd.Timedelta(days=WINDOW_DAYS), end, bench, cpi, rates),
                          period("İlk kayıttan beri", index, index.index[0], end, bench, cpi, rates)]
    else:
        health.periods = [Period("Getiri", why="en az iki günlük değer kaydı gerekir (günlük rapor yazar)")]
    return health


def _pct(x: float | None, sign: bool = True) -> str:
    from core.reports.daily import pct, tr

    if x is None:
        return "ölçülemedi"
    return pct(x) if sign else f"%{tr(x * 100, 1)}"


def text(health: Health) -> str:
    from core.reports.daily import tr

    name = ACCOUNT_NAMES.get(health.account, health.account)
    lines = [f"🩺 Portföy sağlık raporu – {name} ({health.day:%d.%m.%Y})"]
    if not health.weights and not health.unpriced:
        lines += ["Açık pozisyon yok.", DISCLAIMER]
        return "\n".join(lines)
    lines.append(f"Değer: {tr(health.total)} TL" + (" (nakit dahil)" if health.account == "paper" else ""))
    lines.append("Dağılım: " + ", ".join(f"{s.removesuffix('.IS')} {_pct(w, False)}"
                                         for s, w in health.weights.items()))
    if health.weights:
        top, weight = next(iter(health.weights.items()))
        effective = f"{health.effective:.1f}".replace(".", ",") if health.effective else "—"
        lines.append(f"Yoğunlaşma: en büyük pozisyon {top.removesuffix('.IS')} {_pct(weight, False)}; "
                     f"etkin pozisyon sayısı {effective} ({len(health.weights)} hisse)")
    if health.unpriced:
        lines.append("Fiyatı olmayan (hesaba katılmadı): " + ", ".join(s.removesuffix(".IS") for s in health.unpriced))
    if health.corr is None:
        lines.append("Birlikte hareket: ölçülemedi (en az iki hisse ve "
                     f"{MIN_CORR_DAYS} ortak seans gerekir)")
    else:
        lines.append(f"Birlikte hareket: hisseler arası ortalama korelasyon {health.corr:.2f}".replace(".", ",")
                     + f" (son {health.corr_days} seans; 1'e yaklaştıkça çeşitlendirme azalır)")
    lines.append("Getiri (komisyon sonrası, vergi hariç; para giriş-çıkışı ayıklanmış):")
    for p in health.periods:
        if p.nominal is None:
            lines.append(f"  {p.label}: ölçülemedi ({p.why})")
            continue
        excess = _pct(p.nominal - p.bench) if p.bench is not None else "ölçülemedi"
        lines.append(f"  {p.label} ({p.start:%d.%m.%Y} – {p.end:%d.%m.%Y}): nominal {_pct(p.nominal)}, "
                     f"reel {_pct(p.real)}, dolar bazında {_pct(p.usd)}; BIST 100 {_pct(p.bench)}, fark {excess}")
    if any(p.nominal is not None and p.real is None for p in health.periods):
        lines.append("  Reel getiri, dönemi kapsayan TÜFE ayı yayımlanınca hesaplanır.")
    lines.append(DISCLAIMER)
    return "\n".join(lines)


def report(day: date | None = None) -> str:
    """Both accounts with the live files (the real one only when it has holdings)."""

    from core.config.paths import EQUITY_LOG_FILE
    from core.ledger.book import load_ledger
    from core.market import macro
    from core.market.universe import BENCHMARK
    from core.reports.daily import adjusted_bars, read_equity

    entries = load_ledger()
    bench = adjusted_bars(BENCHMARK)
    bench = bench["close"] if len(bench) else pd.Series(dtype=float)
    try:
        cpi = macro.load_cpi()
    except Exception:  # noqa: BLE001 - no CPI file: the real return says "ölçülemedi"
        cpi = None
    try:
        rates = macro.load_usdtry()
    except Exception:  # noqa: BLE001 - no rate file: the dollar return says "ölçülemedi"
        rates = None
    parts = []
    for account in ("real", "paper"):
        equity = read_equity(EQUITY_LOG_FILE, account) if EQUITY_LOG_FILE.exists() else pd.Series(dtype=float)
        h = build(account, day, entries, equity, adjusted_bars, bench, cpi, rates)
        if account == "real" and not h.weights and not h.unpriced:
            continue
        parts.append(text(h))
    return "\n\n".join(parts) or f"🩺 Portföy sağlık raporu: açık pozisyon yok.\n{DISCLAIMER}"


__all__ = ["Health", "Period", "average_correlation", "build", "concentration", "report", "text"]
