"""
QuantBIST
Price data quality report.

    python -m core.market.quality

Checks every stored symbol against the benchmark's trading days:

- missing    trading days the benchmark has but the stock does not
- stale      last candle older than the benchmark's last candle
- zero_volume days without trades
- jumps      moves beyond what BIST's ±10% daily price limit allows
             between two candles; usually an unadjusted corporate
             action (split, bonus issue) or a data error. After a
             market closure (e.g. February 2023) the limit compounds
             over the business days in between, so reopening moves
             are not flagged.
- bad_ohlc   high below low, or close outside the high-low range
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from core.market import store
from core.market.calendar import drop_open_candle
from core.market.universe import BENCHMARK, load_universe

DAILY_LIMIT = 0.105


def suspicious_jumps(df: pd.DataFrame) -> pd.Series:
    """Close-to-close returns the daily price limit cannot explain."""

    if len(df) < 2:
        return pd.Series(dtype=float)

    returns = df["close"].pct_change().iloc[1:]
    days = df.index.values.astype("datetime64[D]")
    sessions = np.maximum(np.busday_count(days[:-1], days[1:]), 1)
    allowed_up = (1 + DAILY_LIMIT) ** sessions - 1
    allowed_down = 1 - (1 - DAILY_LIMIT) ** sessions

    return returns[(returns > allowed_up) | (returns < -allowed_down)]


@dataclass
class SymbolQuality:
    symbol: str
    candles: int
    first: str | None
    last: str | None
    missing: int = 0
    stale_days: int = 0
    zero_volume: int = 0
    jumps: list[str] = field(default_factory=list)
    bad_ohlc: int = 0

    @property
    def ok(self) -> bool:
        return (
            self.candles >= 200
            and self.missing == 0
            and self.stale_days == 0
            and self.bad_ohlc == 0
            and not self.jumps
        )


def check_symbol(
    df: pd.DataFrame,
    symbol: str,
    trading_days: pd.DatetimeIndex | None = None,
) -> SymbolQuality:
    if df.empty:
        return SymbolQuality(symbol=symbol, candles=0, first=None, last=None)

    result = SymbolQuality(
        symbol=symbol,
        candles=len(df),
        first=df.index[0].date().isoformat(),
        last=df.index[-1].date().isoformat(),
    )

    if trading_days is not None and len(trading_days):
        window = trading_days[
            (trading_days >= df.index[0]) & (trading_days <= df.index[-1])
        ]
        result.missing = int(len(window.difference(df.index)))

        newer = trading_days[trading_days > df.index[-1]]
        result.stale_days = int(len(newer))

    result.zero_volume = int((df["volume"] <= 0).sum())

    big = suspicious_jumps(df)
    result.jumps = [f"{d.date()} {r:+.1%}" for d, r in big.items()]

    bad = (df["high"] < df["low"]) | (df["close"] > df["high"] * 1.001) | (
        df["close"] < df["low"] * 0.999
    )
    result.bad_ohlc = int(bad.sum())

    return result


def build_report(symbols: list[str] | None = None) -> list[SymbolQuality]:
    symbols = symbols or load_universe()

    benchmark = drop_open_candle(store.read(BENCHMARK))
    trading_days = benchmark.index if not benchmark.empty else None

    report = [check_symbol(benchmark, BENCHMARK)]

    for symbol in symbols:
        df = drop_open_candle(store.read(symbol))
        report.append(check_symbol(df, symbol, trading_days))

    return report


def format_report(report: list[SymbolQuality]) -> str:
    lines = [
        f"{'Sembol':<10} {'Mum':>5} {'İlk':>10} {'Son':>10} "
        f"{'Eksik':>5} {'Bayat':>5} {'0 hacim':>7} {'Hatalı':>6}  Durum / sıçramalar",
    ]

    for q in report:
        state = "OK" if q.ok else "KONTROL"
        jumps = ", ".join(q.jumps[:3]) + (" ..." if len(q.jumps) > 3 else "")

        lines.append(
            f"{q.symbol:<10} {q.candles:>5} {q.first or '-':>10} {q.last or '-':>10} "
            f"{q.missing:>5} {q.stale_days:>5} {q.zero_volume:>7} {q.bad_ohlc:>6}  "
            f"{state}{'  ' + jumps if jumps else ''}"
        )

    return "\n".join(lines)


def main() -> None:
    print(format_report(build_report()))


if __name__ == "__main__":
    main()


__all__ = [
    "SymbolQuality",
    "check_symbol",
    "suspicious_jumps",
    "build_report",
    "format_report",
]
