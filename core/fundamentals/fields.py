"""Fundamental fields for /tara (E madde 1, the user's 11.11.2026 decision).

Every value comes from data/fundamentals.csv and is usable from the day after its publication (K-48, K-57): no
look-ahead. KAP tables are cumulative from the start of the year, so the 12-month figures (TTM) are
    this period + last year end − the same period last year     (a year-end period is its own TTM).
A field that cannot be computed is NaN ("veri yok"): it never counts as 0, and a screen condition on it is not met
(core.screen.engine names the stock). A change or a TTM that mixes inflation-adjusted (TMS 29) and unadjusted
tables is not computed. Definitions:

| field | definition |
|---|---|
| piyasa_degeri | close × paid-in capital (shares), milyar TL |
| pd_dd | market value / equity (equity ≤ 0: none) |
| fk | market value / TTM net income (a loss: none) |
| ozkaynak_karliligi | TTM net income / equity × 100 (equity ≤ 0: none) |
| borc_ozkaynak | financial debt / equity (equity ≤ 0: none) |
| gelir_artisi_yillik | year-to-date revenue against the same period last year, % |
| gelir_artisi_ceyreklik | the quarter's revenue against the same quarter last year, % |
| fso | market value / TTM revenue (price/sales) |
| piotroski | Piotroski F (core.fundamentals.scores; needs this and last year's same period) |
| altman_z | Altman Z (core.fundamentals.scores) |
"""

from __future__ import annotations

import math
from datetime import date

import pandas as pd

NAMES = ("piyasa_degeri", "pd_dd", "fk", "ozkaynak_karliligi", "borc_ozkaynak", "gelir_artisi_yillik",
         "gelir_artisi_ceyreklik", "fso", "piotroski", "altman_z")
TEXTS = {
    "piyasa_degeri": ("kapanış × ödenmiş sermaye (pay adedi)", "milyar TL"),
    "pd_dd": ("piyasa değeri / özkaynak (özkaynak ≤ 0: veri yok)", "×"),
    "fk": ("piyasa değeri / son 12 ay net kâr (zarar: veri yok)", "×"),
    "ozkaynak_karliligi": ("son 12 ay net kâr / özkaynak × 100", "%"),
    "borc_ozkaynak": ("finansal borç / özkaynak", "×"),
    "gelir_artisi_yillik": ("yıl başından hasılat, geçen yılın aynı dönemine göre (TMS 29 geçişinde yok)", "%"),
    "gelir_artisi_ceyreklik": ("çeyreğin hasılatı, geçen yılın aynı çeyreğine göre (TMS 29 geçişinde yok)", "%"),
    "fso": ("piyasa değeri / son 12 ay hasılat (fiyat/satış)", "×"),
    "piotroski": ("Piotroski F puanı (0–9)", "puan"),
    "altman_z": ("Altman Z", "puan"),
}

_CACHE: dict = {}


def _data() -> pd.DataFrame:
    from core.config.paths import FUNDAMENTALS_FILE
    from core.fundamentals.store import load

    try:
        stamp = FUNDAMENTALS_FILE.stat().st_mtime_ns
    except OSError:
        stamp = None
    if _CACHE.get("stamp") != stamp or "data" not in _CACHE:
        _CACHE.update(stamp=stamp, data=load())
    return _CACHE["data"]


def _prepared(data: pd.DataFrame, code: str) -> pd.DataFrame:
    part = data[data["symbol"] == code].copy()
    if part.empty:
        return part
    part["published"] = pd.to_datetime(part["published_at"], utc=True).dt.tz_convert("Europe/Istanbul")
    part["usable"] = part["published"].dt.normalize().dt.tz_localize(None) + pd.Timedelta(days=1)
    part["value"] = part["value"].astype(float)
    return part


def _known(part: pd.DataFrame, day: pd.Timestamp) -> pd.DataFrame:
    return part[part["usable"] <= day]


def _at(known: pd.DataFrame, item: str, period: str) -> tuple[float | None, str]:
    """(value, inflation flag) of `item` for `period`: the newest publication, consolidated first."""

    rows = known[(known["item"] == item) & (known["period_end"] == period)]
    if rows.empty:
        return None, ""
    best = rows.sort_values(["consolidated", "published"]).iloc[-1]
    return float(best["value"]), str(best.get("inflation_adjusted", ""))


def _same_basis(*flags: str) -> bool:
    known = {f for f in flags if f in ("0", "1")}
    return len(known) <= 1


def _shift(period: str, years: int = 0, month: int | None = None) -> str:
    y, m, _ = (int(x) for x in period.split("-"))
    y -= years
    m = month or m
    last = {3: 31, 6: 30, 9: 30, 12: 31}[m]
    return f"{y:04d}-{m:02d}-{last:02d}"


def _ttm(known: pd.DataFrame, item: str, period: str) -> float | None:
    cur, f0 = _at(known, item, period)
    if cur is None:
        return None
    if period.endswith("-12-31"):
        return cur
    year_end, f1 = _at(known, item, _shift(period, years=1, month=12))
    before, f2 = _at(known, item, _shift(period, years=1))
    if year_end is None or before is None or not _same_basis(f0, f1, f2):
        return None
    return cur + year_end - before


def _quarter(known: pd.DataFrame, item: str, period: str) -> tuple[float | None, str]:
    cur, f0 = _at(known, item, period)
    if cur is None:
        return None, f0
    month = int(period[5:7])
    if month == 3:
        return cur, f0
    earlier, f1 = _at(known, item, _shift(period, month=month - 3))
    if earlier is None or not _same_basis(f0, f1):
        return None, f0
    return cur - earlier, f0


def _growth(new: float | None, old: float | None) -> float | None:
    if new is None or old is None or old <= 0:
        return None
    return (new / old - 1) * 100


def _snapshot(known: pd.DataFrame) -> dict:
    """The parts that do not depend on the price, from the newest period known."""

    if known.empty:
        return {}
    period = sorted(known["period_end"].unique())[-1]
    out = {"period": period}
    shares, _ = _at(known, "paid_in_capital", period)
    equity, _ = _at(known, "total_equity", period)
    debt, _ = _at(known, "financial_debt", period)
    out.update(shares=shares, equity=equity, debt=debt, ni=_ttm(known, "net_income", period),
               rev=_ttm(known, "revenue", period))
    ytd, f0 = _at(known, "revenue", period)
    ytd_before, f1 = _at(known, "revenue", _shift(period, years=1))
    out["growth_y"] = _growth(ytd, ytd_before) if _same_basis(f0, f1) else None
    q, g0 = _quarter(known, "revenue", period)
    q_before, g1 = _quarter(known, "revenue", _shift(period, years=1))
    out["growth_q"] = _growth(q, q_before) if _same_basis(g0, g1) else None
    from core.fundamentals import scores
    from core.fundamentals.store import ITEMS

    cur = {i: v for i in ITEMS if (v := _at(known, i, period)[0]) is not None}
    prev_period = _shift(period, years=1)
    prev = {i: v for i in ITEMS if (v := _at(known, i, prev_period)[0]) is not None}
    flags = {_at(known, i, period)[1] for i in cur} | {_at(known, i, prev_period)[1] for i in prev}
    try:
        f, _ = scores.piotroski(cur, prev) if _same_basis(*flags) else (None, {})
    except Exception:  # noqa: BLE001 - a score that cannot be computed is "veri yok"
        f = None
    try:
        z = scores.altman(cur)
        z = z if isinstance(z, (int, float)) else None  # None or "uygulanamaz" (no current/non-current split)
    except Exception:  # noqa: BLE001
        z = None
    out.update(piotroski=f, altman_z=z)
    return out


def _value(name: str, snap: dict, close: float) -> float:
    nan = math.nan
    shares, equity = snap.get("shares"), snap.get("equity")
    mv = shares * close if shares is not None and close == close else None
    positive_equity = equity is not None and equity > 0
    if name == "piyasa_degeri":
        return mv / 1e9 if mv is not None else nan
    if name == "pd_dd":
        return mv / equity if mv is not None and positive_equity else nan
    if name == "fk":
        ni = snap.get("ni")
        return mv / ni if mv is not None and ni is not None and ni > 0 else nan
    if name == "fso":
        rev = snap.get("rev")
        return mv / rev if mv is not None and rev is not None and rev > 0 else nan
    if name == "ozkaynak_karliligi":
        ni = snap.get("ni")
        return ni / equity * 100 if ni is not None and positive_equity else nan
    if name == "borc_ozkaynak":
        debt = snap.get("debt")
        return debt / equity if debt is not None and positive_equity else nan
    key = {"gelir_artisi_yillik": "growth_y", "gelir_artisi_ceyreklik": "growth_q", "piotroski": "piotroski",
           "altman_z": "altman_z"}[name]
    found = snap.get(key)
    return float(found) if found is not None else nan


def series(symbol: str, name: str, index: pd.DatetimeIndex, close: pd.Series, data: pd.DataFrame | None = None
           ) -> pd.Series:
    """`name` on every day of `index` (NaN where it cannot be computed)."""

    if name not in NAMES:
        raise KeyError(name)
    code = symbol.removesuffix(".IS")
    part = _prepared(_data() if data is None else data, code)
    out = pd.Series(math.nan, index=index, dtype=float)
    if part.empty or len(index) == 0:
        return out
    changes = sorted(d for d in part["usable"].unique() if d <= index[-1])
    if not changes:
        return out
    close = close.reindex(index)
    bounds = [*changes, None]
    for start, end in zip(bounds[:-1], bounds[1:]):
        mask = (index >= start) & ((index < end) if end is not None else True)
        if not mask.any():
            continue
        snap = _snapshot(_known(part, pd.Timestamp(start)))
        out[mask] = [_value(name, snap, float(c)) for c in close[mask]]
    return out


def latest(symbol: str, day: date, close: float, data: pd.DataFrame | None = None) -> dict[str, float]:
    """Every field on `day` (for /temel and the detail lines)."""

    index = pd.DatetimeIndex([pd.Timestamp(day)])
    return {n: float(series(symbol, n, index, pd.Series([close], index=index), data).iloc[0]) for n in NAMES}


__all__ = ["NAMES", "TEXTS", "latest", "series"]
