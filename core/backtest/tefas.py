"""
QuantBIST
Money market fund prices from TEFAS: the return on idle cash in Aşama 3 (docs/RESEARCH_LOG.md).

    python -m core.backtest.tefas --select 2023-07-31 --start 2023-07-31 --out data/cash/ppf.csv

The fund is chosen by a rule fixed before any data was seen: the money market fund (title
contains "PARA PİYASASI") with the largest portfolio on the selection day. Prices are the
daily unit price, fees included. Public data, no account; GitHub runs it (TEFAS is not
reachable from every network).
"""

from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

URL = "https://www.tefas.gov.tr/api/DB/BindHistoryInfo"
HEADERS = {
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://www.tefas.gov.tr",
    "Referer": "https://www.tefas.gov.tr/TarihselVeriler.aspx",
    "User-Agent": "Mozilla/5.0",
}
CHUNK_DAYS = 28  # TEFAS answers short ranges; longer ones are asked in pieces
MONEY_MARKET = "PARA PİYASASI"


def _rows(start: date, end: date, code: str = "", post=None) -> list[dict]:
    post = post or __import__("httpx").post
    data = {"fontip": "YAT", "sfontur": "", "fonkod": code, "fongrup": "", "bastarih": f"{start:%d.%m.%Y}",
            "bittarih": f"{end:%d.%m.%Y}", "fonturkod": "", "fonunvantip": ""}
    response = post(URL, data=data, headers=HEADERS, timeout=60)
    response.raise_for_status()
    return response.json().get("data") or []


def _day(value) -> pd.Timestamp:
    return pd.to_datetime(int(value), unit="ms").normalize()


def select_fund(day: date, post=None) -> tuple[str, str]:
    """(code, title) of the largest money market fund on `day`."""

    funds = [r for r in _rows(day, day, post=post) if MONEY_MARKET in str(r.get("FONUNVAN", "")).upper()]
    if not funds:
        raise RuntimeError(f"TEFAS: {day} için para piyasası fonu bulunamadı")
    best = max(funds, key=lambda r: float(r.get("PORTFOYBUYUKLUK") or 0))
    return str(best["FONKODU"]), str(best["FONUNVAN"])


def fund_history(code: str, start: date, end: date, post=None) -> pd.Series:
    prices: dict[pd.Timestamp, float] = {}
    lo = start
    while lo <= end:
        hi = min(lo + timedelta(days=CHUNK_DAYS - 1), end)
        for r in _rows(lo, hi, code=code, post=post):
            if r.get("FONKODU") == code and r.get("FIYAT") not in (None, "", 0):
                prices[_day(r["TARIH"])] = float(r["FIYAT"])
        lo = hi + timedelta(days=1)
    return pd.Series(prices, dtype=float).sort_index()


def missing_business_days(prices: pd.Series, start: date, end: date) -> list[date]:
    """Weekdays without a price (holidays included; the caller compares with the BIST calendar)."""

    have = {d.date() for d in prices.index}
    return [d.date() for d in pd.bdate_range(start, end) if d.date() not in have]


def write_prices(prices: pd.Series, code: str, path: Path) -> None:
    out = pd.DataFrame({"date": prices.index.date, "price": prices.values, "source": f"TEFAS {code} birim fiyatı"})
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(path, index=False, encoding="utf-8", lineterminator="\n")


def main(argv: list[str] | None = None) -> int:
    from core.infrastructure.console import utf8_output
    from core.market.calendar import holidays

    utf8_output()
    parser = argparse.ArgumentParser(description="TEFAS money market fund prices (cash return).")
    parser.add_argument("--select", type=date.fromisoformat, required=True, help="selection day (rule in RESEARCH_LOG)")
    parser.add_argument("--start", type=date.fromisoformat, required=True)
    parser.add_argument("--end", type=date.fromisoformat, default=date.today())
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    code, name = select_fund(args.select)
    print(f"Seçilen fon ({args.select} en büyük para piyasası fonu): {code} - {name}")
    prices = fund_history(code, args.start, args.end)
    missing = [d for d in missing_business_days(prices, args.start, min(args.end, prices.index[-1].date()))
               if d not in holidays()]
    write_prices(prices, code, args.out)
    print(f"{len(prices)} gün, {prices.index[0].date()} – {prices.index[-1].date()}; "
          f"fiyat {prices.iloc[0]:.6f} → {prices.iloc[-1]:.6f}")
    print(f"Tatil dışı fiyatı olmayan hafta içi gün: {len(missing)}"
          + (f" ({', '.join(str(d) for d in missing[:10])}{' …' if len(missing) > 10 else ''})" if missing else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["fund_history", "missing_business_days", "select_fund", "write_prices"]
