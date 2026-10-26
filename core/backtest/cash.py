"""
QuantBIST
Return on idle cash in the backtest.

Three models (BacktestConfig.cash):

- None                 no interest (the original behaviour; default)
- FixedRate(0.40)      one net annual SIMPLE rate, e.g. "what if cash earned 40%"
- RateSeries(...)      a dated series of annual simple rates (policy or deposit
                       rate) with an optional dated withholding-tax table
- FundPrices(...)      the daily unit price of a money market fund (TEFAS)

Conventions (see the Stage 1 report):

- Turkish rates are quoted as annual SIMPLE rates on an ACT/365 basis.
  Cash compounds daily over CALENDAR days: a weekend earns three days.
  r = 45% simple -> (1 + 0.45/365) ** 365 - 1 = 56.8% effective per year.
- Only information known on a day is used. A rate row carries the date
  from which it APPLIES (for a policy-rate decision: the session after
  the announcement); a deposit-rate row must carry its publication date.
- Withholding tax reduces the gross rate (net = gross * (1 - tax)).
  For fund prices it is applied to the daily gain, which approximates
  tax paid on the gain at redemption.
- Missing data is never estimated: days without a known rate or fund
  price earn nothing and are counted in `missing_days`.

The rate series never feed a trading rule; they only change the value
of cash. The settlement rule (sale proceeds earn interest only after
T+2) lives in the engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

DAYS_PER_YEAR = 365


def _calendar_days(prev_day: pd.Timestamp, day: pd.Timestamp) -> pd.DatetimeIndex:
    """Calendar days whose interest is earned between two closes: (prev_day, day]."""

    return pd.date_range(prev_day + pd.Timedelta(days=1), day, freq="D")


def _as_of(series: pd.Series, days: pd.DatetimeIndex) -> pd.Series:
    """Value in force on each day (last row dated on or before it); NaN before the first row."""

    series = series.sort_index()
    return series.reindex(series.index.union(days)).ffill().reindex(days)


@dataclass(frozen=True)
class CashGrowth:
    factor: float
    missing_days: int = 0


class FixedRate:
    """One net annual simple rate for the whole test."""

    def __init__(self, annual_rate: float):
        self.annual_rate = float(annual_rate)

    def growth(self, prev_day: pd.Timestamp, day: pd.Timestamp) -> CashGrowth:
        days = len(_calendar_days(prev_day, day))
        return CashGrowth((1 + self.annual_rate / DAYS_PER_YEAR) ** days)

    def __repr__(self) -> str:
        return f"FixedRate({self.annual_rate:.4f})"


@dataclass
class RateSeries:
    """
    Dated annual simple rates.

    rates:       index = date from which the rate applies, values = gross rate (0.45 = 45%)
    withholding: index = date from which the tax rate applies, values = tax (0.15 = 15%)
    spread:      subtracted from the gross rate (e.g. what a bank pays below policy)
    """

    rates: pd.Series
    withholding: pd.Series | float = 0.0
    spread: float = 0.0
    name: str = "rate series"

    def _net_daily(self, days: pd.DatetimeIndex) -> pd.Series:
        gross = _as_of(self.rates, days) - self.spread
        if isinstance(self.withholding, pd.Series):
            tax = _as_of(self.withholding, days).fillna(0.0)
        else:
            tax = float(self.withholding)
        return gross * (1 - tax)

    def growth(self, prev_day: pd.Timestamp, day: pd.Timestamp) -> CashGrowth:
        days = _calendar_days(prev_day, day)
        net = self._net_daily(days)
        known = net.dropna()
        factor = float((1 + known / DAYS_PER_YEAR).prod())
        return CashGrowth(factor, int(net.isna().sum()))

    def __repr__(self) -> str:
        return f"RateSeries({self.name})"


@dataclass
class FundPrices:
    """
    Daily unit prices of a money market fund. The price published for a
    day already contains the fund's fees and its daily compounding.
    """

    prices: pd.Series
    withholding: pd.Series | float = 0.0
    name: str = "money market fund"

    def __post_init__(self):
        self.prices = self.prices.dropna().sort_index()

    def growth(self, prev_day: pd.Timestamp, day: pd.Timestamp) -> CashGrowth:
        first, last = self.prices.index[0], self.prices.index[-1]
        if prev_day < first or day > last:
            return CashGrowth(1.0, len(_calendar_days(prev_day, day)))
        start = _as_of(self.prices, pd.DatetimeIndex([prev_day])).iloc[0]
        end = _as_of(self.prices, pd.DatetimeIndex([day])).iloc[0]
        gain = end / start - 1
        if isinstance(self.withholding, pd.Series):
            tax = _as_of(self.withholding, pd.DatetimeIndex([day])).fillna(0.0).iloc[0]
        else:
            tax = float(self.withholding)
        return CashGrowth(1 + gain * (1 - tax))

    def __repr__(self) -> str:
        return f"FundPrices({self.name})"


# ---------------------------------------------------------------------------
# Loaders. Every CSV row must name its source; rows without one are refused.
# ---------------------------------------------------------------------------


def _read(path: Path | str, date_col: str, value_col: str) -> pd.Series:
    df = pd.read_csv(path, comment="#")
    missing = {date_col, value_col, "source"} - set(df.columns)
    if missing:
        raise ValueError(f"{path}: missing columns {sorted(missing)}")
    if df["source"].isna().any() or (df["source"].astype(str).str.strip() == "").any():
        raise ValueError(f"{path}: every row needs a source")
    df[date_col] = pd.to_datetime(df[date_col])
    if df[date_col].duplicated().any():
        raise ValueError(f"{path}: duplicate dates")
    return df.set_index(date_col)[value_col].astype(float).sort_index()


def load_rate_series(
    path: Path | str,
    withholding: Path | str | float | None = None,
    spread: float = 0.0,
) -> RateSeries:
    """
    CSV columns: effective_date, rate (0.45 = 45%), source.
    For a policy-rate decision, effective_date is the session after the
    announcement; for a published deposit rate, the publication date.
    """

    rates = _read(path, "effective_date", "rate")
    tax = load_withholding(withholding) if isinstance(withholding, (str, Path)) else (withholding or 0.0)
    return RateSeries(rates, tax, spread, name=Path(path).stem)


def load_fund_prices(path: Path | str, withholding: Path | str | float | None = None) -> FundPrices:
    """CSV columns: date, price, source (e.g. 'TEFAS <fund code>')."""

    prices = _read(path, "date", "price")
    tax = load_withholding(withholding) if isinstance(withholding, (str, Path)) else (withholding or 0.0)
    return FundPrices(prices, tax, name=Path(path).stem)


def load_withholding(path: Path | str) -> pd.Series:
    """CSV columns: effective_date, rate (0.15 = 15%), source."""

    return _read(path, "effective_date", "rate")


def parse_cash_option(text: str | None):
    """
    Command-line form:
      none | fixed:0.40 | rate:<csv>[,tax=<csv or number>][,spread=0.02] | fund:<csv>[,tax=...]
    """

    if not text or text == "none":
        return None
    kind, _, rest = text.partition(":")
    parts = rest.split(",")
    target, options = parts[0], dict(p.split("=", 1) for p in parts[1:])
    tax = options.get("tax")
    if tax is not None:
        try:
            tax = float(tax)
        except ValueError:
            pass
    if kind == "fixed":
        return FixedRate(float(target))
    if kind == "rate":
        return load_rate_series(target, tax, float(options.get("spread", 0.0)))
    if kind == "fund":
        return load_fund_prices(target, tax)
    raise ValueError(f"unknown cash option: {text}")


__all__ = [
    "CashGrowth",
    "FixedRate",
    "RateSeries",
    "FundPrices",
    "load_rate_series",
    "load_fund_prices",
    "load_withholding",
    "parse_cash_option",
]
