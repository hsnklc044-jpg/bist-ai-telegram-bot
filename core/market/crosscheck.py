"""
QuantBIST
Second-source check of the stored prices.

    python -m core.market.crosscheck                 # universe, last 30 days
    python -m core.market.crosscheck --days 60 --symbols THYAO ASELS

The prices come from Yahoo Finance. This compares their daily closes
with İş Yatırım's public price history (the HisseTekil data behind its
website; free, no key, unofficial: it may change or stop, and it is
used here only to check our data, about one request per stock).

Yahoo's closes are adjusted for dividends and splits, İş Yatırım's
HGDG_KAPANIS is the price as traded, so the levels differ by a constant
factor. The check therefore compares DAILY RETURNS on the days both
sources have:
- a return difference above RETURN_TOLERANCE on one day is listed. When
  our (adjusted) return is HIGHER than the traded one, the traded price
  fell by something the adjusted series removes: a dividend, bonus issue
  or split ("olası düzeltme günü"; also when the day is in
  data/corporate_actions.csv). When it is LOWER, nothing explains it:
  "açıklanamayan", a data error to check on KAP. A wrong spike up in our
  data is caught on the day it reverses;
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

import pandas as pd

from core.infrastructure.logger import get_logger

logger = get_logger(__name__)

URL = "https://www.isyatirim.com.tr/_layouts/15/Isyatirim.Website/Common/Data.aspx/HisseTekil"
RETURN_TOLERANCE = 0.01  # 1 percentage point
MIN_COMMON_DAYS = 5  # fewer sessions in both sources: not checked
TIMEOUT = 60


def fetch_isyatirim(code: str, start: date, end: date, get=None) -> pd.DataFrame:
    """Daily close / high / low / VWAP / TL volume, as traded, oldest first."""

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
        }
        for r in payload.get("value") or []
    ]
    if not rows:
        return pd.DataFrame(columns=["close", "high", "low", "vwap", "volume_tl"])
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

    @property
    def unexplained(self) -> list[tuple[date, float, float, bool]]:
        return [d for d in self.differences if not d[3]]

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

    window = ours[(ours.index >= theirs.index[0]) & (ours.index <= theirs.index[-1])]
    result.only_ours = [d.date() for d in window.index.difference(theirs.index)]
    result.only_theirs = [d.date() for d in theirs.index.difference(window.index)]

    both = pd.concat({"ours": window["close"], "theirs": theirs["close"]}, axis=1, sort=True).dropna()
    result.days = len(both)
    if result.days < MIN_COMMON_DAYS:
        result.error = f"ortak gün {result.days}; karşılaştırılamadı"
        return result
    returns = both.pct_change().dropna()
    actions = actions or set()
    for day, row in returns.iterrows():
        gap = row["ours"] - row["theirs"]
        if abs(gap) > tolerance:
            explained = day.date() in actions or gap > 0
            result.differences.append((day.date(), float(row["ours"]), float(row["theirs"]), explained))
    return result


def _pct(x: float) -> str:
    return f"{x * 100:+.1f}%"


def _days(days: list[date], limit: int = 5) -> str:
    shown = ", ".join(f"{d:%d.%m.%Y}" for d in days[:limit])
    return shown + (f" (+{len(days) - limit})" if len(days) > limit else "")


def format_report(results: list[CrossCheck], period: str) -> str:
    counts = {s: sum(r.state == s for r in results) for s in ("tutarlı", "fark var", "kontrol edilemedi")}
    lines = [
        f"İkinci kaynak kontrolü (İş Yatırım, {period}, günlük getiri farkı > "
        f"{RETURN_TOLERANCE * 100:.0f} puan): {len(results)} hisse | "
        + ", ".join(f"{k} {v}" for k, v in counts.items())
        + f" | karşılaştırılan {sum(r.days for r in results)} hisse-gün",
        f"Açıklanamayan fark {sum(len(r.unexplained) for r in results)} gün; olası düzeltme günü "
        f"(temettü/bedelsiz/bölünme) {sum(len(r.explained) for r in results)} gün",
    ]
    for r in results:
        if r.state == "tutarlı":
            continue
        code = r.symbol.removesuffix(".IS")
        if r.error:
            lines.append(f"  {code}: kontrol edilemedi ({r.error})")
            continue
        parts = [
            f"{day:%d.%m.%Y} Yahoo {_pct(a)} / İş {_pct(b)}" for day, a, b, _ in r.unexplained[:5]
        ]
        if len(r.unexplained) > 5:
            parts.append(f"+{len(r.unexplained) - 5} gün daha")
        if r.only_ours:
            parts.append(f"yalnız Yahoo'da {len(r.only_ours)} gün: {_days(r.only_ours)}")
        if r.only_theirs:
            parts.append(f"yalnız İş Yatırım'da {len(r.only_theirs)} gün: {_days(r.only_theirs)}")
        lines.append(f"  {code}: " + "; ".join(parts))
    lines.append(
        "Not: düzeltilmiş seride getirinin işlem fiyatından yüksek olduğu günler temettü/bedelsiz/bölünme "
        "kaynaklı sayılır; açıklanamayan farklar ve tek kaynakta olan günler KAP'tan kontrol edilmelidir."
    )
    return "\n".join(lines)


def run(
    symbols: list[str],
    days: int = 30,
    today: date | None = None,
    get=None,
    bars=None,
    start: date | None = None,
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
    for symbol in symbols:
        code = symbol.removesuffix(".IS")
        try:
            theirs = fetch_isyatirim(code, start, today, get=get)
        except Exception as exc:  # noqa: BLE001 - one failed stock must not stop the check
            logger.warning("Second source failed | %s | %s", symbol, exc)
            results.append(CrossCheck(symbol, error=f"{type(exc).__name__}: {str(exc)[:80]}"))
            continue
        results.append(compare(symbol, bars(symbol), theirs, actions.get(symbol) or actions.get(code)))
    return results


def main(argv: list[str] | None = None) -> None:
    from core.market.universe import load_universe

    parser = argparse.ArgumentParser(description="Compare stored closes with İş Yatırım's price history.")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--start", type=date.fromisoformat, default=None, help="YYYY-MM-DD (instead of --days)")
    parser.add_argument("--symbols", nargs="*", help="codes (default: data/universe.csv)")
    parser.add_argument("--universe", choices=("today", "pit"), default="today",
                        help="pit: every BIST 100 member since 2022 (the research universe)")
    parser.add_argument("--adjusted", action="store_true",
                        help="check the corporate-action adjusted series the backtests use")
    args = parser.parse_args(argv)

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
    print(format_report(results, period + (", düzeltilmiş seri" if args.adjusted else "")))


if __name__ == "__main__":
    main()


__all__ = ["CrossCheck", "compare", "fetch_isyatirim", "format_report", "run"]
