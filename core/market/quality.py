"""
QuantBIST
Price data quality report.

    python -m core.market.quality

Trading days are decided by majority: a date is a session if at least
half of the checked symbols have a candle with volume on it. (Using
only XU100 is not enough; Yahoo's index series skips some sessions,
for example 25 December.)

Per symbol:

- missing     sessions the majority traded but the symbol has no candle
- stale       sessions after the symbol's last candle
- zero_volume candles with zero volume (Yahoo volume gaps)
- jumps       daily moves larger than ±20% that are not market-wide.
              BIST's daily price limit is ±10% of the base price, so
              such a move is almost always an unadjusted bonus/rights
              issue or split (or a data error). Moves of 10-20% do occur
              in Yahoo's adjusted data (dividend adjustment, base price
              rules) and are not flagged. A suggested factor for
              data/corporate_actions.csv is printed for each jump;
              `--apply-suggestions` writes them to the file.
- breaches    (information only) moves beyond the ±10% limit, compounded
              over the business days since the previous candle, that
              stay under ±20% and are not market-wide. They never mark
              a symbol for exclusion. Drops are listed first: a dividend
              adjustment cannot explain a drop, an unadjusted rights
              issue (bedelli) can, so those are worth checking on KAP.
- bad_ohlc    high below low, or close outside the high-low range

Cancelled sessions and corporate actions (core.market.corrections)
are applied before checking.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from core.market import store
from core.market.calendar import drop_open_candle
from core.market.corrections import clean
from core.market.universe import BENCHMARK, load_universe

DAILY_LIMIT = 0.20
# BIST's limit is ±10% of the base price rounded to the price tick, so a
# real limit-up/limit-down close can land slightly beyond 10%.
SESSION_LIMIT = 0.105
MARKET_WIDE_SHARE = 0.5
ZERO_VOLUME_LIMIT = 0.02


@dataclass
class Jump:
    date: str
    change: float
    suggested_factor: float

    def __str__(self) -> str:
        return f"{self.date} {self.change:+.1%} (factor≈{self.suggested_factor:.4f})"


@dataclass
class SymbolQuality:
    symbol: str
    candles: int
    first: str | None
    last: str | None
    missing: int = 0
    stale_days: int = 0
    zero_volume: int = 0
    jumps: list[Jump] = field(default_factory=list)
    bad_ohlc: int = 0
    breaches: list[Jump] = field(default_factory=list)

    @property
    def zero_volume_share(self) -> float:
        return self.zero_volume / self.candles if self.candles else 0.0

    @property
    def problems(self) -> list[str]:
        result = []
        if self.candles < 200:
            result.append("kısa geçmiş")
        if self.missing > 2:
            result.append("eksik gün")
        if self.stale_days:
            result.append("bayat")
        if self.bad_ohlc:
            result.append("hatalı OHLC")
        if self.jumps:
            result.append("düzeltilmemiş sıçrama")
        if self.zero_volume_share > ZERO_VOLUME_LIMIT:
            result.append("hacim eksik")
        return result

    @property
    def ok(self) -> bool:
        return not self.problems


def trading_calendar(frames: dict[str, pd.DataFrame]) -> pd.DatetimeIndex:
    """Dates on which at least half of the symbols traded."""

    traded = [df.index[df["volume"] > 0] for df in frames.values() if not df.empty]

    if not traded:
        return pd.DatetimeIndex([])

    counts = pd.Series(1, index=traded[0]).groupby(level=0).sum()
    for idx in traded[1:]:
        counts = counts.add(pd.Series(1, index=idx), fill_value=0)

    days = counts[counts >= len(traded) * MARKET_WIDE_SHARE].index

    return pd.DatetimeIndex(sorted(days))


def market_wide_moves(frames: dict[str, pd.DataFrame]) -> set[pd.Timestamp]:
    """Dates on which most symbols moved beyond the daily limit together."""

    flags = []
    for df in frames.values():
        if len(df) > 1:
            flags.append((df["close"].pct_change().abs() > DAILY_LIMIT).rename(None))

    if not flags:
        return set()

    table = pd.concat(flags, axis=1, sort=True).fillna(False)
    share = table.mean(axis=1)

    return set(share[share >= MARKET_WIDE_SHARE].index)


def limit_breaches(df: pd.DataFrame, market_wide: set[pd.Timestamp] | None = None) -> pd.Series:
    """
    Close-to-close moves the daily price limit cannot produce: beyond
    SESSION_LIMIT compounded over the business days since the previous
    candle (so a reopening after a closure is not flagged), and not on a
    market-wide day.
    """

    if len(df) < 2:
        return pd.Series(dtype=float)

    returns = df["close"].pct_change().iloc[1:]
    days = df.index.values.astype("datetime64[D]")
    sessions = np.maximum(np.busday_count(days[:-1], days[1:]), 1)
    up = (1 + SESSION_LIMIT) ** sessions - 1
    down = 1 - (1 - SESSION_LIMIT) ** sessions

    flagged = returns[(returns > up) | (returns < -down)]

    return flagged[~flagged.index.isin(list(market_wide or ()))]


def check_symbol(
    df: pd.DataFrame,
    symbol: str,
    trading_days: pd.DatetimeIndex | None = None,
    market_wide: set[pd.Timestamp] | None = None,
    exceptions=None,
) -> SymbolQuality:
    from core.market.corrections import real_moves

    if df.empty:
        return SymbolQuality(symbol=symbol, candles=0, first=None, last=None)

    result = SymbolQuality(
        symbol=symbol,
        candles=len(df),
        first=df.index[0].date().isoformat(),
        last=df.index[-1].date().isoformat(),
    )

    if trading_days is not None and len(trading_days):
        window = trading_days[(trading_days >= df.index[0]) & (trading_days <= df.index[-1])]
        result.missing = int(len(window.difference(df.index)))
        result.stale_days = int(len(trading_days[trading_days > df.index[-1]]))

    result.zero_volume = int((df["volume"] <= 0).sum())

    returns = df["close"].pct_change().dropna()
    big = returns[returns.abs() > DAILY_LIMIT]

    real = real_moves(symbol, exceptions)  # moves a second source showed real (data/candle_exceptions.csv)
    for day, change in big.items():
        if (market_wide and day in market_wide) or day.date() in real:
            continue
        result.jumps.append(
            Jump(
                date=day.date().isoformat(),
                change=float(change),
                suggested_factor=round(1 + float(change), 4),
            )
        )

    jumped = {j.date for j in result.jumps}
    for day, change in limit_breaches(df, market_wide).items():
        if day.date().isoformat() in jumped:
            continue
        result.breaches.append(
            Jump(
                date=day.date().isoformat(),
                change=float(change),
                suggested_factor=round(1 + float(change), 4),
            )
        )

    bad = (
        (df["high"] < df["low"])
        | (df["close"] > df["high"] * 1.001)
        | (df["close"] < df["low"] * 0.999)
    )
    result.bad_ohlc = int(bad.sum())

    return result


def build_report(symbols: list[str] | None = None) -> list[SymbolQuality]:
    symbols = [BENCHMARK, *(symbols or load_universe())]

    frames = {s: drop_open_candle(clean(store.read(s), s)) for s in symbols}
    stocks = {s: df for s, df in frames.items() if s != BENCHMARK}

    calendar = trading_calendar(frames)
    market_wide = market_wide_moves(stocks)

    return [check_symbol(frames[s], s, calendar, market_wide) for s in symbols]


def format_report(report: list[SymbolQuality]) -> str:
    lines = [
        f"{'Sembol':<10} {'Mum':>5} {'İlk':>10} {'Son':>10} "
        f"{'Eksik':>5} {'Bayat':>5} {'0 hacim':>7} {'Hatalı':>6}  Durum",
    ]

    for q in report:
        state = "OK" if q.ok else "KONTROL: " + ", ".join(q.problems)

        lines.append(
            f"{q.symbol:<10} {q.candles:>5} {q.first or '-':>10} {q.last or '-':>10} "
            f"{q.missing:>5} {q.stale_days:>5} {q.zero_volume:>7} {q.bad_ohlc:>6}  {state}"
        )

    jumps = [(q.symbol, j) for q in report for j in q.jumps]

    if jumps:
        lines += [
            "",
            "±%20'yi aşan düzeltilmemiş sıçramalar (sermaye artırımı/bölünme). KAP'tan doğrulayıp",
            "data/corporate_actions.csv dosyasına ekleyin ya da --apply-suggestions kullanın:",
        ]
        lines += [f"  {symbol},{j.date},{j.suggested_factor},{j.change:+.1%}" for symbol, j in jumps]

    breaches = [(q.symbol, b) for q in report for b in q.breaches]
    drops = sorted((x for x in breaches if x[1].change < 0), key=lambda x: x[1].change)
    rises = sorted((x for x in breaches if x[1].change > 0), key=lambda x: -x[1].change)

    if breaches:
        lines += [
            "",
            f"Bilgi: ±%10 günlük limitle açıklanamayan, %20 altı hareketler ({len(breaches)}; "
            "hisseler dışlanmaz).",
        ]
        if drops:
            lines.append(
                "  Düşüşler: temettü düzeltmesiyle açıklanamaz; fiyata yansımamış bedelli olabilir, "
                "KAP'tan kontrol edin:"
            )
            lines += [f"    {s},{b.date},{b.suggested_factor},{b.change:+.1%}" for s, b in drops]
        if rises:
            lines.append("  Yükselişler: çoğunlukla Yahoo'nun temettü/baz fiyat düzeltmesi:")
            lines += [f"    {s},{b.date},{b.change:+.1%}" for s, b in rises]

    return "\n".join(lines)


def apply_suggestions(report: list[SymbolQuality], path=None) -> int:
    """Append suggested corporate-action rows for every flagged jump."""

    from core.market.corrections import CORPORATE_ACTIONS_FILE, load_corporate_actions

    path = path or CORPORATE_ACTIONS_FILE
    existing = {(a.symbol, a.ex_date.isoformat()) for a in load_corporate_actions(path)}
    header = "symbol,ex_date,kind,ratio,price,factor,source,note\n"
    text = path.read_text(encoding="utf-8") if path.exists() else header
    old_format = not text.splitlines()[0].startswith("symbol,ex_date,kind")

    def row(symbol, jump) -> str:
        note = f"otomatik öneri {jump.change:+.1%} (KAP ile doğrulanmadı)"
        if old_format:
            return f"{symbol},{jump.date},{jump.suggested_factor},{note}"
        return f"{symbol},{jump.date},factor,,,{jump.suggested_factor},,{note}"

    rows = [
        row(q.symbol, j)
        for q in report
        for j in q.jumps
        if (q.symbol, j.date) not in existing
    ]

    if not rows:
        return 0

    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text + "\n".join(rows) + "\n", encoding="utf-8")

    return len(rows)


def recent_suspects(report: list[SymbolQuality], since: str, known: set[tuple[str, str]] | None = None) -> list[dict]:
    """Jumps (likely an unadjusted bonus/rights issue or split) and limit breaches on or after
    `since` that data/corporate_actions.csv does not explain yet. Nothing is applied."""

    known = known or set()
    found = []
    for r in report:
        for kind, moves in (("sıçrama", r.jumps), ("limit aşımı", r.breaches)):
            for j in moves:
                if j.date >= since and (r.symbol, j.date) not in known:
                    found.append({"symbol": r.symbol, "date": j.date, "change": j.change, "kind": kind,
                                  "suggested_factor": j.suggested_factor})
    return sorted(found, key=lambda f: (f["date"], f["symbol"]))


def format_suspects(found: list[dict], since: str) -> str:
    lines = [f"Kurumsal işlem şüphesi taraması ({since} sonrası): " + (f"{len(found)} yeni şüphe" if found else
                                                                     "yeni şüphe yok")]
    for f in found:
        lines.append(f"  {f['symbol'].removesuffix('.IS')} {f['date'][8:10]}.{f['date'][5:7]}.{f['date'][:4]} "
                     f"{f['change'] * 100:+.1f}% {f['kind']} (çarpan önerisi {f['suggested_factor']})")
    if found:
        lines.append("Yapılacak: her satırı KAP'ta (bedelsiz/bedelli/bölünme/temettü) doğrula; doğrulananı kaynağıyla "
                     "data/corporate_actions.csv'ye ekle. Hiçbir şey otomatik uygulanmadı.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Price data quality report")
    parser.add_argument(
        "--apply-suggestions",
        action="store_true",
        help="write suggested factors for flagged jumps to data/corporate_actions.csv",
    )
    parser.add_argument("--recent", type=int, default=None, metavar="GÜN",
                        help="only the corporate-action suspects of the last N days (every BIST 100 member since 2022)")
    args = parser.parse_args(argv)

    if args.recent:
        from datetime import date, timedelta

        from core.market.corrections import load_corporate_actions
        from core.market.membership import ever_members

        since = (date.today() - timedelta(days=args.recent)).isoformat()
        known = {(a.symbol, a.ex_date.isoformat()) for a in load_corporate_actions()}
        found = recent_suspects(build_report(ever_members()), since, known)
        print(format_suspects(found, f"{since[8:10]}.{since[5:7]}.{since[:4]}"))
        return

    report = build_report()

    if args.apply_suggestions:
        added = apply_suggestions(report)
        print(f"{added} satır data/corporate_actions.csv dosyasına eklendi.\n")
        report = build_report()

    print(format_report(report))


if __name__ == "__main__":
    main()


__all__ = [
    "SymbolQuality",
    "Jump",
    "trading_calendar",
    "market_wide_moves",
    "limit_breaches",
    "check_symbol",
    "build_report",
    "format_report",
    "apply_suggestions",
]
