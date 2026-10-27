"""
QuantBIST
Second-source check of the stored prices.

    python -m core.market.crosscheck                 # universe, last 30 days
    python -m core.market.crosscheck --days 60 --symbols THYAO ASELS

The prices come from Yahoo Finance. This compares their daily closes
with İş Yatırım's public price history (the HisseTekil data behind its
website; free, no key, unofficial: it may change or stop, and it is
used here only to check our data, about one request per stock).

Both series are adjusted, but not necessarily the same way or from the
same date: Yahoo adjusts for dividends and splits; İş Yatırım's
HGDG_KAPANIS is adjusted for bonus issues (KCAER, 28.11.2024, a 191%
bonus issue: İş Yatırım -0.2%) and showed no dividend gaps on large
payers. Levels can therefore differ by a factor; the check compares
DAILY RETURNS on the days both sources have:
- a return difference above RETURN_TOLERANCE on one day is listed as
  unexplained, unless the day is a recorded corporate action in
  data/corporate_actions.csv. (An earlier version counted every day where
  our return was higher as a likely dividend; that assumed İş Yatırım
  was unadjusted, which the KCAER case disproved.);
- a gap undone the next session (opposite signs, summing to about zero)
  is ONE wrong close in our data: counted as "tek gün kapanış hatası";
  it does not change long-run returns but distorts that day's close;
- sessions present in one source only are listed.

    python -m core.market.crosscheck --start 2022-01-01 --universe pit --adjusted
checks the full history the backtests use (former BIST 100 members,
corporate actions applied); about 12 seconds per stock.
A stock whose second-source data cannot be fetched is reported as
"kontrol edilemedi", never as consistent.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from core.infrastructure.logger import get_logger

logger = get_logger(__name__)

URL = "https://www.isyatirim.com.tr/_layouts/15/Isyatirim.Website/Common/Data.aspx/HisseTekil"
RETURN_TOLERANCE = 0.01  # 1 percentage point
MARKET_WIDE_SHARE = 0.20  # a date where this share of checked stocks differ is a source-level issue
RETRIES = 3
CHUNK_DAYS = 370  # long ranges are fetched year by year (the service times out on long ones)
MIN_COMMON_DAYS = 5  # fewer sessions in both sources: not checked
TIMEOUT = 60
SOURCE_DOWN_AFTER = 3  # this many stocks failing in a row: the source is down, the rest are not asked


def fetch_isyatirim(code: str, start: date, end: date, get=None, sleep=None) -> pd.DataFrame:
    """Daily close / high / low / VWAP / TL volume, as traded, oldest first.

    Fetched in yearly pieces, each retried up to RETRIES times with a growing pause.
    """

    import time

    sleep = sleep or time.sleep
    pieces, piece_start = [], start
    while piece_start <= end:
        piece_end = min(piece_start + timedelta(days=CHUNK_DAYS - 1), end)
        for attempt in range(RETRIES):
            try:
                pieces.append(_fetch_piece(code, piece_start, piece_end, get))
                break
            except Exception:  # noqa: BLE001 - retried, then raised
                if attempt == RETRIES - 1:
                    raise
                sleep(5 * (attempt + 1))
        piece_start = piece_end + timedelta(days=1)

    pieces = [p for p in pieces if not p.empty]
    if not pieces:
        return pd.DataFrame(columns=["close", "high", "low", "vwap", "volume_tl", "index"])
    df = pd.concat(pieces)
    return df[~df.index.duplicated()].sort_index()


def _fetch_piece(code: str, start: date, end: date, get=None) -> pd.DataFrame:
    if get is None:
        import requests

        get = requests.get

    response = get(
        URL,
        params={"hisse": code, "startdate": f"{start:%d-%m-%Y}", "enddate": f"{end:%d-%m-%Y}"},
        headers={"User-Agent": "Mozilla/5.0 (QuantBIST data check)"},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("ok"):
        raise ValueError(payload.get("errorDescription") or "İş Yatırım hata döndürdü")

    rows = [
        {
            "date": pd.Timestamp(pd.to_datetime(r["HGDG_TARIH"], format="%d-%m-%Y")),
            "close": float(r["HGDG_KAPANIS"]),
            "high": float(r["HGDG_MAX"]),
            "low": float(r["HGDG_MIN"]),
            "vwap": float(r["HGDG_AOF"]),
            "volume_tl": float(r["HGDG_HACIM"]),
            # BIST 100 on that day, sent with every row (END_ENDEKS_KODU 01)
            "index": float(r["END_DEGER"]) if r.get("END_DEGER") is not None else float("nan"),
        }
        for r in payload.get("value") or []
    ]
    if not rows:
        return pd.DataFrame(columns=["close", "high", "low", "vwap", "volume_tl", "index"])
    return pd.DataFrame(rows).set_index("date").sort_index()


@dataclass
class CrossCheck:
    symbol: str
    days: int = 0  # sessions both sources have
    only_ours: list[date] = field(default_factory=list)
    only_theirs: list[date] = field(default_factory=list)
    # day, our return, their return, explained (adjustment day or recorded corporate action)
    differences: list[tuple[date, float, float, bool]] = field(default_factory=list)
    error: str = ""
    market_days: set[date] = field(default_factory=set)  # source-level dates, set by format_report
    close_errors: list[date] = field(default_factory=list)  # one wrong close, undone the next session
    fixes: list[tuple[date, float]] = field(default_factory=list)  # factor that makes our close right

    @property
    def mismatched(self) -> list[tuple[date, float, float, bool]]:
        """Differences no adjustment explains (market-wide days included)."""

        return [d for d in self.differences if not d[3]]

    @property
    def unexplained(self) -> list[tuple[date, float, float, bool]]:
        """Stock-specific: not explained and not on a market-wide date."""

        return [d for d in self.mismatched if d[0] not in self.market_days]

    @property
    def explained(self) -> list[tuple[date, float, float, bool]]:
        return [d for d in self.differences if d[3]]

    @property
    def state(self) -> str:
        if self.error:
            return "kontrol edilemedi"
        if self.unexplained or self.only_ours or self.only_theirs:
            return "fark var"
        return "tutarlı"


def compare(
    symbol: str,
    ours: pd.DataFrame,
    theirs: pd.DataFrame,
    actions: set[date] | None = None,
    tolerance: float = RETURN_TOLERANCE,
) -> CrossCheck:
    result = CrossCheck(symbol)
    if theirs.empty:
        result.error = "ikinci kaynakta veri yok"
        return result
    if ours is None or ours.empty or not isinstance(ours.index, pd.DatetimeIndex):
        result.error = "Yahoo'da (depoda) veri yok"
        return result

    window = ours[(ours.index >= theirs.index[0]) & (ours.index <= theirs.index[-1])]
    result.only_ours = [d.date() for d in window.index.difference(theirs.index)]
    result.only_theirs = [d.date() for d in theirs.index.difference(window.index)]

    both = pd.concat({"ours": window["close"], "theirs": theirs["close"]}, axis=1, sort=True).dropna()
    result.days = len(both)
    if result.days < MIN_COMMON_DAYS:
        result.error = f"ortak gün {result.days}; karşılaştırılamadı"
        return result
    returns = both.pct_change().dropna()
    gaps = returns["ours"] - returns["theirs"]
    actions = actions or set()
    days = list(returns.index)
    paired: set = set()
    # one wrong close: the gap on one day is undone the next session
    for i in range(len(days) - 1):
        a, b = gaps.iloc[i], gaps.iloc[i + 1]
        if abs(a) > tolerance and abs(b) > tolerance and a * b < 0 and abs(a + b) <= tolerance:
            if days[i] not in paired:
                paired.update((days[i], days[i + 1]))
                result.close_errors.append(days[i].date())
                # our close on that day should have moved like theirs from the previous close
                previous = both["ours"].shift(1).loc[days[i]]
                right = previous * (1 + returns["theirs"].iloc[i])
                result.fixes.append((days[i].date(), float(right / both["ours"].loc[days[i]])))
    for day, row in returns.iterrows():
        gap = gaps.loc[day]
        if abs(gap) > tolerance and day not in paired:
            explained = day.date() in actions
            result.differences.append((day.date(), float(row["ours"]), float(row["theirs"]), explained))
    return result


def _pct(x: float) -> str:
    return f"{x * 100:+.1f}%"


def _days(days: list[date], limit: int = 5) -> str:
    shown = ", ".join(f"{d:%d.%m.%Y}" for d in days[:limit])
    return shown + (f" (+{len(days) - limit})" if len(days) > limit else "")


def market_wide_days(results: list[CrossCheck]) -> dict[date, tuple[int, float]]:
    """Dates where many stocks differ the same day: {day: (stocks, median gap)}."""

    checked = [r for r in results if not r.error]
    gaps: dict[date, list[float]] = {}
    for r in checked:
        for day, a, b, _ in r.mismatched:
            gaps.setdefault(day, []).append(a - b)
    limit = max(3, MARKET_WIDE_SHARE * len(checked))
    return {d: (len(g), float(pd.Series(g).median())) for d, g in sorted(gaps.items()) if len(g) >= limit}


def _benchmark_line(b: CrossCheck, market: dict) -> list[str]:
    if b.error:
        return [f"XU100: kontrol edilemedi ({b.error})"]
    lines = [f"XU100 (İş Yatırım'ın BIST 100 değeriyle, {b.days} gün): "
             + ("tutarlı" if not b.mismatched else f"{len(b.mismatched)} günde fark")]
    for day, a, c, _ in b.mismatched[:10]:
        tag = " — piyasa geneli farkla aynı gün" if day in market else ""
        lines.append(f"  {day:%d.%m.%Y} Yahoo {_pct(a)} / İş {_pct(c)}{tag}")
    if len(b.mismatched) > 10:
        lines.append(f"  +{len(b.mismatched) - 10} gün daha")
    return lines


def format_report(results: list[CrossCheck], period: str, show_explained: bool = False) -> str:
    from core.market.universe import BENCHMARK

    benchmark = next((r for r in results if r.symbol == BENCHMARK), None)
    results = [r for r in results if r.symbol != BENCHMARK]
    market = market_wide_days(results)
    for r in results:
        r.market_days = set(market)
    counts = {s: sum(r.state == s for r in results) for s in ("tutarlı", "fark var", "kontrol edilemedi")}
    lines = [
        f"İkinci kaynak kontrolü (İş Yatırım, {period}, günlük getiri farkı > "
        f"{RETURN_TOLERANCE * 100:.0f} puan): {len(results)} hisse | "
        + ", ".join(f"{k} {v}" for k, v in counts.items())
        + f" | karşılaştırılan {sum(r.days for r in results)} hisse-gün",
        f"Hisseye özgü açıklanamayan fark {sum(len(r.unexplained) for r in results)} gün; kayıtlı şirket işlemi "
        f"günü {sum(len(r.explained) for r in results)}; "
        f"tek gün kapanış hatası (ertesi gün düzelen) {sum(len(r.close_errors) for r in results)}",
    ]
    wrong_closes: dict[date, int] = {}
    for r in results:
        for d in r.close_errors:
            wrong_closes[d] = wrong_closes.get(d, 0) + 1
    common = {d: n for d, n in sorted(wrong_closes.items()) if n >= max(3, MARKET_WIDE_SHARE * len(results))}
    if common:
        lines.append("Çok hissede aynı gün yanlış kapanış (Yahoo):")
        lines += [f"  {d:%d.%m.%Y}: {n} hisse" for d, n in common.items()]
    if market:
        lines.append(
            f"Piyasa geneli farklar (kontrol edilen hisselerin en az %{MARKET_WIDE_SHARE * 100:.0f}'i aynı gün; "
            "kaynak düzeyinde sorun, hisse hatası değil):"
        )
        lines += [f"  {d:%d.%m.%Y}: {n} hisse, medyan fark {_pct(g)} (Yahoo − İş)" for d, (n, g) in market.items()]
    if benchmark is not None:
        lines += _benchmark_line(benchmark, market)
    lines.append("Hisseye özgü farklar (piyasa geneli günler hariç):")
    for r in results:
        if r.state == "tutarlı":
            continue
        code = r.symbol.removesuffix(".IS")
        if r.error:
            lines.append(f"  {code}: kontrol edilemedi ({r.error})")
            continue
        own = r.unexplained
        parts = [f"{day:%d.%m.%Y} Yahoo {_pct(a)} / İş {_pct(b)}" for day, a, b, _ in own[:5]]
        if len(own) > 5:
            parts.append(f"+{len(own) - 5} gün daha")
        if r.only_ours:
            parts.append(f"yalnız Yahoo'da {len(r.only_ours)} gün: {_days(r.only_ours)}")
        if r.only_theirs:
            parts.append(f"yalnız İş Yatırım'da {len(r.only_theirs)} gün: {_days(r.only_theirs)}")
        if show_explained and r.explained:
            parts.append("düzeltme günü sayılanlar: " + ", ".join(
                f"{day:%d.%m.%Y} Yahoo {_pct(a)} / İş {_pct(b)}" for day, a, b, _ in r.explained
            ))
        if parts:
            lines.append(f"  {code}: " + "; ".join(parts))
    lines.append(
        "Not: iki kaynak da düzeltilmiş fiyat verir ama düzeltme yöntemleri aynı olmayabilir; açıklanamayan "
        "farklar ve tek kaynakta olan günler KAP ve üçüncü bir kaynaktan kontrol edilmeden düzeltilmez."
    )
    return "\n".join(lines)


def summary(results: list[CrossCheck], day: date) -> dict:
    """For the 'veri doğruluğu' objective: stocks checked, stocks with an unexplained difference.
    Call after format_report (it marks the market-wide dates)."""

    from core.market.universe import BENCHMARK

    stocks = [r for r in results if r.symbol != BENCHMARK]
    checked = [r for r in stocks if not r.error]
    differing = sorted(r.symbol.removesuffix(".IS") for r in checked if r.state == "fark var")
    return {
        "date": day.isoformat(),
        "checked": len(checked),
        "differing": differing,
        "unchecked": sorted(r.symbol.removesuffix(".IS") for r in stocks if r.error),
        "share": len(differing) / len(checked) if checked else None,
    }


def export_fixes(results: list[CrossCheck], path) -> int:
    """Write the one-day wrong closes as price fixes (core.market.corrections)."""

    import csv

    rows = [(r.symbol, d, f) for r in results for d, f in r.fixes]
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(["symbol", "date", "factor", "source", "note"])
        for symbol, day, factor in rows:
            writer.writerow([symbol, day.isoformat(), f"{factor:.6f}", "isyatirim", "tek gün kapanış hatası"])
    return len(rows)


def run(
    symbols: list[str],
    days: int = 30,
    today: date | None = None,
    get=None,
    bars=None,
    start: date | None = None,
    sleep=None,
) -> list[CrossCheck]:
    from core.market.corrections import load_corporate_actions

    if bars is None:
        from core.reports.daily import raw_bars as bars

    today = today or date.today()
    start = start or today - timedelta(days=days)
    actions: dict[str, set[date]] = {}
    for a in load_corporate_actions():
        actions.setdefault(a.symbol, set()).add(a.ex_date)

    results = []
    index_values: list[pd.Series] = []
    failed_in_row = 0
    for symbol in symbols:
        code = symbol.removesuffix(".IS")
        if failed_in_row >= SOURCE_DOWN_AFTER:
            results.append(CrossCheck(symbol, error=f"ikinci kaynak yanıt vermiyor ({SOURCE_DOWN_AFTER} hisse üst üste)"))
            continue
        try:
            theirs = fetch_isyatirim(code, start, today, get=get, sleep=sleep)
        except Exception as exc:  # noqa: BLE001 - one failed stock must not stop the check
            logger.warning("Second source failed | %s | %s", symbol, exc)
            results.append(CrossCheck(symbol, error=f"{type(exc).__name__}: {str(exc)[:80]}"))
            failed_in_row += 1
            continue
        failed_in_row = 0
        if "index" in theirs:
            index_values.append(theirs["index"].dropna())
        try:
            results.append(compare(symbol, bars(symbol), theirs, actions.get(symbol) or actions.get(code)))
        except Exception as exc:  # noqa: BLE001 - one bad stock must not stop a long run
            logger.exception("Comparison failed | %s", symbol)
            results.append(CrossCheck(symbol, error=f"karşılaştırma hatası: {type(exc).__name__}: {str(exc)[:80]}"))

    # the benchmark: İş Yatırım sends BIST 100 with every stock row
    from core.market.universe import BENCHMARK

    index = pd.concat(index_values) if index_values else pd.Series(dtype=float)
    index = index[~index.index.duplicated()].sort_index()
    benchmark = compare(BENCHMARK, bars(BENCHMARK), index.to_frame("close")) if len(index) else CrossCheck(
        BENCHMARK, error="ikinci kaynakta endeks değeri yok"
    )
    benchmark.differences = [(d, a, b, False) for d, a, b, _ in benchmark.differences]  # no adjustments on an index
    return [benchmark, *results]


SAME_CLOSE = 0.005  # within 0.5%: the same close


def _price(x) -> str:
    if x is None or pd.isna(x):
        return "—"
    return f"{x:.2f}" if abs(x) >= 1 else f"{x:.4f}"


def _row(label: str, day, o, h, low, c) -> str:
    return "  " + label.ljust(12) + f"{day:%d.%m.%Y}".ljust(12) + "".join(_price(v).ljust(8) for v in (o, h, low, c))


def inspect(items: list[tuple[str, date]], get=None, bars=None, sleep=None, around: int = 2) -> list[str]:
    """One suspicious candle per item: our raw candle and İş Yatırım's, `around` sessions each side.

    İş Yatırım gives no open, so the open column is ours only. Nothing is changed."""

    if bars is None:
        from core.reports.daily import raw_bars as bars

    lines = []
    for symbol, day in items:
        code = symbol.removesuffix(".IS")
        title = f"{code} {day:%d.%m.%Y}"
        ours = bars(symbol)
        try:
            theirs = fetch_isyatirim(code, day - timedelta(days=10), day + timedelta(days=10), get=get, sleep=sleep)
        except Exception as exc:  # noqa: BLE001 - one failed stock must not stop the check
            lines += [f"{title}: ikinci kaynak alınamadı ({type(exc).__name__})", ""]
            continue
        target = pd.Timestamp(day)
        notes = []
        if target in ours.index and target in theirs.index:
            diff = ours.at[target, "close"] / theirs.at[target, "close"] - 1
            notes.append("kapanış aynı" if abs(diff) <= SAME_CLOSE else f"kapanış farklı (%{diff * 100:+.1f})")
            bar = ours.loc[target]
            if not bar["low"] <= bar["close"] <= bar["high"]:
                notes.append("bizde en yüksek/en düşük kapanışı kapsamıyor")
        elif target not in ours.index and target not in theirs.index:
            notes.append("o gün iki kaynakta da yok")
        else:
            notes.append("o gün " + ("bizde yok" if target not in ours.index else "İş Yatırım'da yok"))
        lines.append(f"{title}: " + " | ".join(notes))
        lines.append("  " + "kaynak".ljust(12) + "gün".ljust(12) + "".join(c.ljust(8) for c in
                                                                           ("açılış", "yüksek", "düşük", "kapanış")))
        days = sorted(set(ours.index) | set(theirs.index))
        before = [d for d in days if d < target][-around:]
        after = [d for d in days if d > target][:around]
        days = before + ([target] if target in days else []) + after
        for d in days:
            if d in ours.index:
                b = ours.loc[d]
                lines.append(_row("bizde", d, b["open"], b["high"], b["low"], b["close"]))
            if d in theirs.index:
                t = theirs.loc[d]
                lines.append(_row("İş Yatırım", d, None, t["high"], t["low"], t["close"]))
        lines.append("")
    return lines


def main(argv: list[str] | None = None) -> None:
    from core.market.universe import load_universe

    parser = argparse.ArgumentParser(description="Compare stored closes with İş Yatırım's price history.")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--start", type=date.fromisoformat, default=None, help="YYYY-MM-DD (instead of --days)")
    parser.add_argument("--symbols", nargs="*", help="codes (default: data/universe.csv)")
    parser.add_argument("--universe", choices=("today", "pit"), default="today",
                        help="pit: every BIST 100 member since 2022 (the research universe)")
    parser.add_argument("--export", default=None, help="write one-day wrong closes as price fixes (CSV)")
    parser.add_argument("--show-explained", action="store_true",
                        help="also list the days counted as dividend/bonus/split days")
    parser.add_argument("--adjusted", action="store_true",
                        help="check the corporate-action adjusted series the backtests use")
    parser.add_argument("--summary", default=None, help="write the accuracy summary (JSON) here")
    parser.add_argument("--inspect", nargs="*", default=None, metavar="KOD:YYYY-MM-DD",
                        help="show our raw candle and İş Yatırım's around these days, nothing else")
    args = parser.parse_args(argv)

    if args.inspect:
        items = []
        for item in args.inspect:
            code, _, day = item.partition(":")
            items.append((code.upper() if code.upper().endswith(".IS") else f"{code.upper()}.IS",
                          date.fromisoformat(day)))
        print("\n".join(["Ham mum karşılaştırması (bizde: Yahoo, işlem gördüğü haliyle; düzeltme uygulanmaz)", "",
                         *inspect(items)]))
        return

    if args.symbols:
        symbols = [s if s.endswith(".IS") else f"{s.upper()}.IS" for s in args.symbols]
    elif args.universe == "pit":
        from core.market.membership import ever_members

        symbols = ever_members()
    else:
        symbols = load_universe()

    if args.adjusted:
        from core.reports.daily import adjusted_bars as bars
    else:
        from core.reports.daily import raw_bars as bars

    period = f"{args.start:%d.%m.%Y} – bugün" if args.start else f"son {args.days} gün"
    results = run(symbols, args.days, bars=bars, start=args.start)
    print(format_report(results, period + (", düzeltilmiş seri" if args.adjusted else ""), args.show_explained))
    if args.summary:
        import json

        Path(args.summary).parent.mkdir(parents=True, exist_ok=True)
        Path(args.summary).write_text(json.dumps(summary(results, date.today()), indent=1), encoding="utf-8")
    if args.export:
        print(f"{export_fixes(results, args.export)} günlük kapanış düzeltmesi yazıldı: {args.export}")


if __name__ == "__main__":
    main()


__all__ = ["CrossCheck", "compare", "fetch_isyatirim", "format_report", "inspect", "run", "summary"]
