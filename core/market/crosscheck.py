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
- a return difference above RETURN_TOLERANCE on one day is listed; on an
  ex-dividend or split day it is expected (marked when the day is in
  data/corporate_actions.csv), on any other day it points to a data error;
- sessions present in one source only are listed.
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
    differences: list[tuple[date, float, float, bool]] = field(default_factory=list)  # day, ours, theirs, known action
    error: str = ""

    @property
    def unexplained(self) -> list[tuple[date, float, float, bool]]:
        return [d for d in self.differences if not d[3]]

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
        if abs(row["ours"] - row["theirs"]) > tolerance:
            result.differences.append((day.date(), float(row["ours"]), float(row["theirs"]), day.date() in actions))
    return result


def _pct(x: float) -> str:
    return f"{x * 100:+.1f}%"


def format_report(results: list[CrossCheck], days: int) -> str:
    counts = {s: sum(r.state == s for r in results) for s in ("tutarlı", "fark var", "kontrol edilemedi")}
    lines = [
        f"İkinci kaynak kontrolü (İş Yatırım, son {days} gün, günlük getiri farkı > "
        f"{RETURN_TOLERANCE * 100:.0f} puan): {len(results)} hisse | "
        + ", ".join(f"{k} {v}" for k, v in counts.items())
        + f" | karşılaştırılan {sum(r.days for r in results)} hisse-gün",
    ]
    for r in results:
        if r.state == "tutarlı":
            continue
        code = r.symbol.removesuffix(".IS")
        if r.error:
            lines.append(f"  {code}: kontrol edilemedi ({r.error})")
            continue
        parts = []
        for day, a, b, known in r.differences:
            parts.append(f"{day:%d.%m} Yahoo {_pct(a)} / İş {_pct(b)}{' (kayıtlı şirket işlemi)' if known else ''}")
        if r.only_ours:
            parts.append("yalnız Yahoo'da: " + ", ".join(f"{d:%d.%m}" for d in r.only_ours))
        if r.only_theirs:
            parts.append("yalnız İş Yatırım'da: " + ", ".join(f"{d:%d.%m}" for d in r.only_theirs))
        lines.append(f"  {code}: " + "; ".join(parts))
    lines.append(
        "Not: temettü ve bölünme günlerinde fark beklenir (Yahoo fiyatları düzeltilmiş, İş Yatırım işlem "
        "fiyatı); başka günlerdeki fark veri hatasına işaret eder ve KAP'tan kontrol edilmelidir."
    )
    return "\n".join(lines)


def run(symbols: list[str], days: int, today: date | None = None, get=None, bars=None) -> list[CrossCheck]:
    from core.market.corrections import load_corporate_actions

    if bars is None:
        from core.reports.daily import raw_bars as bars

    today = today or date.today()
    start = today - timedelta(days=days)
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
    parser.add_argument("--symbols", nargs="*", help="codes (default: data/universe.csv)")
    args = parser.parse_args(argv)

    symbols = [s if s.endswith(".IS") else f"{s.upper()}.IS" for s in args.symbols] if args.symbols else load_universe()
    print(format_report(run(symbols, args.days), args.days))


if __name__ == "__main__":
    main()


__all__ = ["CrossCheck", "compare", "fetch_isyatirim", "format_report", "run"]
