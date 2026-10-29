"""
QuantBIST
Fundamental scores (profesyonel filtreler Aşama 4, DECISIONS K-57): Piotroski F, Altman Z''
(emerging markets), Beneish M, Greenblatt's earnings yield and return on capital, Novy-Marx's
gross profitability and book-to-market. Formulas were fixed before any data was seen.

Inputs come from the publication-dated store (core.fundamentals.store): a value counts from the day
after its publication. Period t is the newest published period, t−1 the same period a year earlier
(Turkish interim tables are cumulative from January). A missing item is "veri yok", never zero.
These are rule outputs, not advice.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd

DISCLAIMER = "Kural çıktısıdır, öneri değildir. Karar ve sorumluluk kullanıcıdadır."
NOT_APPLICABLE = "uygulanamaz"


def _div(a, b):
    return None if a is None or b is None or b == 0 else a / b


def _get(d: dict, *keys):
    values = [d.get(k) for k in keys]
    return None if any(v is None or v != v for v in values) else values


# --- the scores ----------------------------------------------------------------------------------


def piotroski(cur: dict, prev: dict) -> tuple[int | None, dict[str, bool | None]]:
    """(score 0–9 or None when a part is missing, the nine parts)."""

    def ratio(d, a, b):
        v = _get(d, a, b)
        return None if v is None else _div(*v)

    roa, roa_prev = ratio(cur, "net_income", "total_assets"), ratio(prev, "net_income", "total_assets")
    lev, lev_prev = ratio(cur, "long_term_debt", "total_assets"), ratio(prev, "long_term_debt", "total_assets")
    cr, cr_prev = ratio(cur, "current_assets", "current_liabilities"), ratio(prev, "current_assets", "current_liabilities")
    gm, gm_prev = ratio(cur, "gross_profit", "revenue"), ratio(prev, "gross_profit", "revenue")
    at, at_prev = ratio(cur, "revenue", "total_assets"), ratio(prev, "revenue", "total_assets")
    cfo, ni = cur.get("operating_cash_flow"), cur.get("net_income")
    shares, shares_prev = cur.get("paid_in_capital"), prev.get("paid_in_capital")

    def cmp(a, b, test):
        return None if a is None or b is None else bool(test(a, b))

    parts = {
        "ROA > 0": None if roa is None else roa > 0,
        "nakit akışı > 0": None if cfo is None else cfo > 0,
        "ROA arttı": cmp(roa, roa_prev, lambda a, b: a > b),
        "nakit akışı > net kâr": cmp(cfo, ni, lambda a, b: a > b),
        "borçluluk azaldı": cmp(lev, lev_prev, lambda a, b: a < b),
        "cari oran arttı": cmp(cr, cr_prev, lambda a, b: a > b),
        "yeni pay yok": cmp(shares, shares_prev, lambda a, b: a <= b),
        "brüt marj arttı": cmp(gm, gm_prev, lambda a, b: a > b),
        "varlık devri arttı": cmp(at, at_prev, lambda a, b: a > b),
    }
    if any(v is None for v in parts.values()):
        return None, parts
    return sum(parts.values()), parts


def altman(cur: dict):
    """Altman Z'' (2005, emerging markets). NOT_APPLICABLE without a current / non-current split."""

    if cur.get("current_assets") is None or cur.get("current_liabilities") is None:
        return NOT_APPLICABLE
    v = _get(cur, "current_assets", "current_liabilities", "total_assets", "retained_earnings", "ebit",
             "total_equity", "total_liabilities")
    if v is None:
        return None
    ca, cl, ta, re, ebit, eq, tl = v
    if not ta or not tl:
        return None
    return 3.25 + 6.56 * (ca - cl) / ta + 3.26 * re / ta + 6.72 * ebit / ta + 1.05 * eq / tl


def zone(z: float) -> str:
    return "sıkıntı bölgesi" if z < 1.1 else ("gri bölge" if z <= 2.6 else "güvenli bölge")


def beneish(cur: dict, prev: dict):
    """Beneish M (8 variables, 1999). NOT_APPLICABLE without current assets; None when an item is missing."""

    if cur.get("current_assets") is None:
        return NOT_APPLICABLE
    keys = ("receivables", "revenue", "gross_profit", "current_assets", "ppe", "total_assets", "depreciation",
            "sga", "current_liabilities", "long_term_debt")
    a, b = _get(cur, *keys, "net_income", "operating_cash_flow"), _get(prev, *keys)
    if a is None or b is None:
        return None
    (rec, rev, gp, ca, ppe, ta, dep, sga, cl, ltd, ni, cfo), (rec0, rev0, gp0, ca0, ppe0, ta0, dep0, sga0, cl0, ltd0) = a, b
    try:
        dsri = (rec / rev) / (rec0 / rev0)
        gmi = (gp0 / rev0) / (gp / rev)
        aqi = (1 - (ca + ppe) / ta) / (1 - (ca0 + ppe0) / ta0)
        sgi = rev / rev0
        depi = (dep0 / (dep0 + ppe0)) / (dep / (dep + ppe))
        sgai = (sga / rev) / (sga0 / rev0)
        lvgi = ((cl + ltd) / ta) / ((cl0 + ltd0) / ta0)
        tata = (ni - cfo) / ta
    except ZeroDivisionError:
        return None
    return (-4.84 + 0.920 * dsri + 0.528 * gmi + 0.404 * aqi + 0.892 * sgi + 0.115 * depi - 0.172 * sgai
            + 4.679 * tata - 0.327 * lvgi)


def market_value(cur: dict, price: float | None):
    shares = cur.get("paid_in_capital")
    return None if shares is None or price is None else shares * price


def greenblatt(cur: dict, price: float | None) -> tuple[float | None, float | None]:
    """(earnings yield = EBIT / EV, return on capital = EBIT / (NWC + PPE))."""

    mv = market_value(cur, price)
    v = _get(cur, "ebit", "financial_debt", "cash")
    ey = None if mv is None or v is None else _div(v[0], mv + v[1] - v[2])
    w = _get(cur, "ebit", "current_assets", "current_liabilities", "ppe")
    roc = None if w is None else _div(w[0], (w[1] - w[2]) + w[3])
    return ey, roc


def novy_marx(cur: dict, price: float | None) -> tuple[float | None, float | None]:
    """(gross profitability = GP / TA, book-to-market = equity / market value)."""

    v = _get(cur, "gross_profit", "total_assets")
    gp = None if v is None else _div(*v)
    mv = market_value(cur, price)
    eq = cur.get("total_equity")
    return gp, (None if mv is None or eq is None else _div(eq, mv))


# --- from the store ------------------------------------------------------------------------------


@dataclass
class Snapshot:
    period: str | None = None
    previous_period: str | None = None
    current: dict = field(default_factory=dict)
    previous: dict = field(default_factory=dict)
    tms_switch: bool = False


def snapshot(data: pd.DataFrame, symbol: str, day: date) -> Snapshot:
    """Period t (newest usable before `day`) and t−1 (the same period a year earlier), newest publication each."""

    from core.fundamentals.store import ITEMS, _usable

    code = symbol.removesuffix(".IS")
    usable = {}
    for item in ITEMS:
        part = _usable(data, code, item)
        if not part.empty:
            usable[item] = part[part["usable"] <= pd.Timestamp(day)]
    periods = sorted({p for part in usable.values() for p in part["period_end"]})
    snap = Snapshot()
    if not periods:
        return snap
    snap.period = periods[-1]
    year_ago = f"{int(snap.period[:4]) - 1}{snap.period[4:]}"
    snap.previous_period = year_ago if year_ago in periods else None
    flags = {}
    for item, part in usable.items():
        for period, target in ((snap.period, snap.current), (snap.previous_period, snap.previous)):
            rows = part[part["period_end"] == period] if period else part.iloc[0:0]
            if not rows.empty:
                best = rows.sort_values(["consolidated", "published"]).iloc[-1]
                target[item] = float(best["value"])
                flags.setdefault(period, set()).add(str(best.get("inflation_adjusted", "")))
    if snap.previous_period:
        a, b = flags.get(snap.period, set()), flags.get(snap.previous_period, set())
        snap.tms_switch = bool(a and b and a != b and "" not in a | b)
    return snap


def text(symbol: str, data: pd.DataFrame, day: date, price: float | None) -> str:
    from core.reports.daily import tr

    code = symbol.removesuffix(".IS")
    snap = snapshot(data, symbol, day)
    if snap.period is None:
        return (f"📚 {code} temel puanları: veri yok (data/fundamentals.csv'de bu hisse için yayımlanmış kalem yok; "
                f"K-48).\n{DISCLAIMER}")
    cur, prev = snap.current, snap.previous
    lines = [f"📚 {code} temel puanları – dönem {snap.period}" + (f", karşılaştırma {snap.previous_period}"
                                                               if snap.previous_period else ", bir yıl önceki dönem yok")]
    changes = bool(snap.previous_period) and not snap.tms_switch
    reason = "TMS 29 geçişi (enflasyon düzeltmesi dönemler arasında farklı)" if snap.tms_switch else "önceki dönem yok"

    if changes:
        score, parts = piotroski(cur, prev)
        known = sum(v is not None for v in parts.values())
        lines.append(f"Piotroski F: {score}/9" if score is not None else f"Piotroski F: kısmi ({known}/9 bileşen)")
        lines.append("  " + ", ".join(f"{name} {'✓' if v else '✗' if v is not None else '?'}" for name, v in parts.items()))
    else:
        lines.append(f"Piotroski F: hesaplanmadı ({reason})")

    z = altman(cur)
    lines.append("Altman Z'': " + (z if isinstance(z, str) else "veri yok" if z is None else f"{tr(z, 2)} ({zone(z)})"))
    if changes:
        m = beneish(cur, prev)
        lines.append("Beneish M: " + (m if isinstance(m, str) else "veri yok" if m is None else
                                      f"{tr(m, 2)}" + (" (kazanç kalitesi incelenmeli; hile tespiti değil)" if m > -1.78
                                                       else "")))
    else:
        lines.append(f"Beneish M: hesaplanmadı ({reason})")
    ey, roc = greenblatt(cur, price)
    gp, bm = novy_marx(cur, price)

    def pct(x):
        return "veri yok" if x is None else f"%{tr(x * 100, 1)}"

    lines.append(f"Greenblatt: kazanç getirisi {pct(ey)}, sermaye getirisi {pct(roc)}")
    lines.append(f"Novy-Marx: brüt kârlılık {pct(gp)}, defter/piyasa {'veri yok' if bm is None else tr(bm, 2)}")
    lines += ["Formüller DECISIONS K-57; değer yayımın ertesi gününden itibaren kullanılır.", DISCLAIMER]
    return "\n".join(lines)


def command_text(words: list[str]) -> str:
    from core.fundamentals.store import load
    from core.market.calendar import now_istanbul
    from core.reports.daily import raw_bars
    from core.watchlist.service import normalize_symbol

    if len(words) != 1:
        return "Kullanım:\n/temel THYAO – temel puanlar (Piotroski F, Altman Z'', Beneish M, Greenblatt, Novy-Marx)"
    try:
        symbol = normalize_symbol(words[0])
    except ValueError as exc:
        return str(exc)
    bars = raw_bars(symbol)
    price = float(bars["close"].iloc[-1]) if bars is not None and not bars.empty else None
    return text(symbol, load(), now_istanbul().date(), price)


__all__ = ["command_text", "DISCLAIMER", "NOT_APPLICABLE", "Snapshot", "altman", "beneish", "greenblatt", "novy_marx", "piotroski",
           "snapshot", "text", "zone"]
