"""
QuantBIST
Market context: nominal TL results also read against inflation, the dollar and cash (Talimat C,
DECISIONS K-51). Extra columns only: no primary criterion and no live series changes.

- TÜFE: data/macro/cpi.csv, TÜİK's monthly % changes as TCMB republishes them, each with the day
  TÜİK announced it. A value is used from the day AFTER that day; inside a month nothing is
  estimated, the last published month is carried forward (so a window shorter than a month can
  show real = nominal). The index is chained from the monthly changes; returns only use ratios,
  so the base year (TÜİK moved to 2025=100) does not matter.
- USD/TRY: TCMB's indicative rate bulletin (ForexBuying), one XML per working day at about
  15:30, before the BIST close. A day without a bulletin (holiday, half day) uses the previous
  bulletin. Bulletins are cached in data/macro/usdtry.csv (local, not in git), each day asked once.
- Cash: the policy rate net of withholding, the same series as the research (data/cash).

real  = (1 + nominal) / (CPI_end / CPI_start) - 1
usd   = (1 + nominal) * (USD_start / USD_end) - 1
cash  = (1 + nominal) / cash growth - 1

    python -m core.market.macro --usd 2022-01-03     # fill the USD/TRY cache (1 request per day)
"""

from __future__ import annotations

import argparse
import csv
import logging
import re
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from core.config.paths import DATA_DIR, LOG_DIR

logger = logging.getLogger(__name__)

MACRO_DIR = DATA_DIR / "macro"
CPI_FILE = MACRO_DIR / "cpi.csv"
CPI_LOCAL = MACRO_DIR / "cpi_local.csv"  # months the PC added itself after the repository file (not in git)
CPI_PAGE = ("https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Istatistikler/Enflasyon+Verileri/"
            "Tuketici+Fiyatlari")
USD_FILE = MACRO_DIR / "usdtry.csv"
POLICY_RATE = DATA_DIR / "cash" / "policy_rate.csv"
WITHHOLDING = DATA_DIR / "cash" / "withholding.csv"
BULLETIN_URL = "https://www.tcmb.gov.tr/kurlar/{d:%Y%m}/{d:%d%m%Y}.xml"
TIMEOUT = 15
PAUSE = 0.3  # seconds between bulletin requests
SAVE_EVERY = 50  # bulletins; a stopped run keeps what it fetched
MAX_STALE_DAYS = 10  # calendar days: a 9-day bayram has no bulletin; anything older is "kur yok"
FETCH_FILE = LOG_DIR / "usd_fetch.json"  # the last bulletin run: how many asked, added, and why the rest failed
SECOND_FILE = LOG_DIR / "usd_second_source.json"  # the last TCMB–Yahoo comparison (K-51)
SECOND_LIMIT = 1.0  # % : a bigger gap is a data note in /durum; no value is changed
SOURCE = "TÜFE: TÜİK (TCMB tablosu); kur: TCMB gösterge kuru; nakit: TCMB politika faizi"


def _http_get(url, **kwargs):
    import requests

    return requests.get(url, **kwargs)


# --- TÜFE ------------------------------------------------------------------------------------


def _cpi_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(line for line in fh if not line.startswith("#")))


def load_cpi(path: Path | str | None = None, local: Path | str | None = None) -> pd.DataFrame:
    """Rows by period 'YYYY-MM': monthly_pct, annual_pct, published (Timestamp), index (chained).
    Without a path: the repository file plus the months the PC added (CPI_LOCAL); a repository
    row always wins over a local one."""

    if path is None:
        path, local = CPI_FILE, CPI_LOCAL if local is None else local
    path = Path(path)
    rows = {r["period"]: r for r in _cpi_rows(Path(local))} if local else {}
    rows.update({r["period"]: r for r in _cpi_rows(path)})
    if not rows:
        return pd.DataFrame(columns=["monthly_pct", "annual_pct", "published", "index"])
    df = pd.DataFrame(list(rows.values())).set_index("period").sort_index()
    df["monthly_pct"] = df["monthly_pct"].astype(float)
    df["annual_pct"] = df["annual_pct"].astype(float)
    df["published"] = pd.to_datetime(df["published"])
    for period, published in df["published"].items():
        month_end = pd.Period(period, "M").end_time.normalize()
        if published <= month_end:
            raise ValueError(f"{path}: {period} yayım tarihi {published:%d.%m.%Y} ay bitmeden")
    df["index"] = (1 + df["monthly_pct"] / 100).cumprod()
    return df


@dataclass(frozen=True)
class KnownCpi:
    period: str
    index: float


def cpi_known(cpi: pd.DataFrame, day: date) -> KnownCpi | None:
    """The last month whose CPI was published BEFORE `day` (usable from the next day on)."""

    known = cpi[cpi["published"] < pd.Timestamp(day)]
    if known.empty:
        return None
    return KnownCpi(known.index[-1], float(known["index"].iloc[-1]))


def parse_cpi_page(body: bytes) -> list[tuple[str, float, float]]:
    """(period, monthly %, annual %) rows of TCMB's 'Tüketici Fiyatları' table, newest first."""

    import html

    text = re.sub(r"<script.*?</script>|<style.*?</style>", "", body.decode("utf-8", errors="replace"), flags=re.S)
    text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text)))
    return [(f"{y}-{m}", float(monthly), float(annual))
            for m, y, annual, monthly in re.findall(r"\b(\d\d)-(\d{4}) (-?\d+\.\d\d) (-?\d+\.\d\d)\b", text)]


def update_cpi(today: date, repo: Path | str | None = None, local: Path | str | None = None, get=None) -> bool:
    """After the 3rd of the month a new figure is due: read TCMB's table and add the next months to
    CPI_LOCAL. Each added month is dated the day it was FIRST SEEN, never earlier, so a late or
    rescheduled release can never be used before it existed. Network problems are quiet."""

    repo, local = Path(repo or CPI_FILE), Path(local or CPI_LOCAL)
    cpi = load_cpi(repo, local)
    if cpi.empty:
        return False
    following = pd.Period(cpi.index[-1], "M") + 1
    if today < (following + 1).start_time.date() + timedelta(days=2):
        return False
    try:
        r = (_http_get if get is None else get)(CPI_PAGE, timeout=TIMEOUT, headers={"User-Agent": "Mozilla/5.0 (QuantBIST)"})
        rows = parse_cpi_page(r.content) if r.status_code == 200 else []
    except (OSError, ValueError):
        return False
    found = {period: (monthly, annual) for period, monthly, annual in rows}
    added = []
    while str(following) in found:
        monthly, annual = found[str(following)]
        added.append([str(following), f"{monthly:.2f}", f"{annual:.2f}", today.isoformat(),
                      "ilk görüldüğü gün (otomatik, TCMB tablosu)"])
        following += 1
    if not added:
        return False
    new = not local.exists()
    local.parent.mkdir(parents=True, exist_ok=True)
    with open(local, "a", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        if new:
            w.writerow(["period", "monthly_pct", "annual_pct", "published", "published_note"])
        w.writerows(added)
    return True


def cpi_window(cpi: pd.DataFrame, start: date, end: date) -> tuple[KnownCpi | None, KnownCpi | None]:
    """
    (start level, end level). Validation M24: the start is the end of the month BEFORE the start
    month — a past level, so it only has to be published by `end` (taking the month published by
    `start` added a whole month before the window: 03.01.2022 took December 2021's +13,58%). The
    end is the last month published before `end`; the months after it are never estimated.
    """

    b = cpi_known(cpi, end)
    before = str(pd.Period(start, "M") - 1)
    if b is None or before not in cpi.index or cpi.loc[before, "published"] >= pd.Timestamp(end):
        return None, b
    return KnownCpi(before, float(cpi.loc[before, "index"])), b


def real_return(nominal: float, start: date, end: date, cpi: pd.DataFrame) -> float | None:
    """None when the start is not covered or no new month was published in the window."""

    a, b = cpi_window(cpi, start, end)
    if a is None or b is None or b.period <= a.period:
        return None
    return (1 + nominal) / (b.index / a.index) - 1


# --- USD/TRY ---------------------------------------------------------------------------------


def bulletin_url(day: date) -> str:
    return BULLETIN_URL.format(d=day)


def parse_bulletin(body: bytes) -> tuple[date, float]:
    """(bulletin date, USD ForexBuying) from one TCMB XML."""

    text = body.decode("utf-8", errors="replace")
    stamp = re.search(r'Tarih="(\d\d)\.(\d\d)\.(\d{4})"', text)
    usd = re.search(r'Kod="USD".*?<ForexBuying>([\d.]+)</ForexBuying>', text, flags=re.S)
    if not stamp or not usd:
        raise ValueError("TCMB bülteni okunamadı (tarih ya da USD satırı yok)")
    d, m, y = (int(x) for x in stamp.groups())
    return date(y, m, d), float(usd.group(1))


def _cache(path: Path) -> dict[date, str]:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8", newline="") as fh:
        return {date.fromisoformat(r["date"]): r["rate"] for r in csv.DictReader(fh)}


def load_usdtry(path: Path | str | None = None) -> pd.Series:
    """Bulletin days with a rate (days asked without a bulletin are left out)."""

    rows = {d: float(r) for d, r in _cache(Path(path or USD_FILE)).items() if r}
    series = pd.Series(rows, dtype=float)
    series.index = pd.to_datetime(series.index)
    return series.sort_index()


def _save_cache(path: Path, have: dict[date, str]) -> None:
    import os

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.stem}.{os.getpid()}.tmp")  # the bot and the report are two processes
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["date", "rate"])
        w.writerows((d.isoformat(), have[d]) for d in sorted(have))
    tmp.replace(path)


def update_usdtry(start: date, end: date, path: Path | str | None = None, limit: int | None = None,
                  get=None, sleep=None, budget: float | None = None, clock=None,
                  status: Path | str | None = None) -> int:
    """Ask TCMB for every weekday in [start, end] not yet in the cache; returns the days added.
    A 404 (no bulletin) is remembered as an empty rate; a network error is not remembered.
    `budget` (seconds) stops before a request that would start after it; progress is saved every
    SAVE_EVERY bulletins and at the end, so the next run continues where this one stopped."""

    path = Path(path or USD_FILE)
    get = _http_get if get is None else get
    sleep = time.sleep if sleep is None else sleep
    clock = time.monotonic if clock is None else clock
    have = _cache(path)
    wanted = [d.date() for d in pd.bdate_range(start, end) if d.date() not in have]
    if limit is not None:
        wanted = wanted[:limit]
    began = clock()
    added = asked = 0
    problems: dict[str, int] = {}

    def problem(reason: str) -> None:
        problems[reason] = problems.get(reason, 0) + 1

    for i, day in enumerate(wanted):
        if budget is not None and clock() - began >= budget:
            break
        if i:
            sleep(PAUSE)
        asked += 1
        try:
            r = get(bulletin_url(day), timeout=TIMEOUT, headers={"User-Agent": "Mozilla/5.0 (QuantBIST)"})
        except OSError as exc:
            problem(f"bağlantı hatası ({type(exc).__name__})")
            continue
        if r.status_code == 404:
            have[day] = ""
        elif r.status_code == 200:
            try:
                stamp, rate = parse_bulletin(r.content)
            except ValueError:
                problem("bülten okunamadı")
                continue
            if stamp != day:
                problem("bülten tarihi farklı")
            have[day] = f"{rate:.4f}" if stamp == day else ""
        else:
            problem(f"HTTP {r.status_code}")
            continue
        added += 1
        if added % SAVE_EVERY == 0:
            _save_cache(path, have)
    if added:
        _save_cache(path, have)
    if asked:
        _save_fetch(Path(status or FETCH_FILE), {"day": end.isoformat(), "asked": asked, "added": added,
                                                  "problems": problems})
        if problems:
            logger.warning("USD/TRY bulletins: %d asked, %d added; %s", asked, added, problems)
    return added


BULLETIN_HOUR = 16  # TCMB publishes the day's bulletin at about 15:30 Istanbul time


def refresh_usd(now: datetime, update=None) -> int:
    """The bot's hourly step (v0.99.32): the last two weeks' missing bulletins, at most 10 requests
    in 30 s. Today is asked only after BULLETIN_HOUR: a 404 before publication would be remembered
    as 'no bulletin' for good. Nothing is asked when the cache is complete; errors only reach the log."""

    update = update_usdtry if update is None else update
    today = now.date()
    end = today if now.hour >= BULLETIN_HOUR else today - timedelta(days=1)
    try:
        return update(today - timedelta(days=14), end, limit=10, budget=30)
    except Exception:  # noqa: BLE001 - the bot never stops on this
        logger.exception("USD/TRY refresh failed")
        return 0


def _save_fetch(path: Path, result: dict) -> None:
    import json

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    except OSError:
        logger.warning("USD/TRY fetch status could not be saved")


def _load_fetch(path: Path | None = None) -> dict | None:
    import json

    try:
        return json.loads(Path(path or FETCH_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def forget_empty(start: date, path: Path | str | None = None) -> int:
    """Drop the days from `start` on that were remembered without a rate, so the next run asks again."""

    path = Path(path or USD_FILE)
    have = _cache(path)
    drop = [d for d, r in have.items() if d >= start and not r]
    for d in drop:
        del have[d]
    if drop:
        _save_cache(path, have)
    return len(drop)


def _empty_days(now: date, path: Path | None = None, days: int = 14) -> list[date]:
    return sorted(d for d, r in _cache(Path(path or USD_FILE)).items() if not r and (now - d).days <= days)


def usd_on(rates: pd.Series, day: date) -> float | None:
    """The last bulletin on or before `day`, at most MAX_STALE_DAYS old (a gap in the cache never
    lends a months-old rate to a later day)."""

    known = rates.loc[: pd.Timestamp(day)]
    if not len(known) or (pd.Timestamp(day) - known.index[-1]).days > MAX_STALE_DAYS:
        return None
    return float(known.iloc[-1])


def usd_return(nominal: float, start: date, end: date, rates: pd.Series) -> float | None:
    a, b = usd_on(rates, start), usd_on(rates, end)
    if a is None or b is None:
        return None
    return (1 + nominal) * (a / b) - 1


def second_source_check(rates: pd.Series, today: date | None = None, fetch=None, days: int = 14) -> dict | None:
    """Yahoo's USDTRY=X close against the TCMB bulletin on the days both have in the last `days`.
    Yahoo's daily close is taken at another hour, so small gaps are normal (K-51: > 1% is a note)."""

    today = today or date.today()
    start = today - timedelta(days=days)
    try:
        if fetch is None:
            from core.market.provider import get_provider

            fetch = _second_fetch or get_provider().fetch  # the store's provider (Yahoo on the PC)
        yahoo = fetch(["USDTRY=X"], start).get("USDTRY=X")
    except Exception:  # noqa: BLE001 - a second source never stops anything
        return None
    if yahoo is None or yahoo.empty:
        return None
    both = pd.concat([rates.loc[pd.Timestamp(start):], yahoo["close"]], axis=1, join="inner").dropna()
    if both.empty:
        return None
    gaps = (both.iloc[:, 1] / both.iloc[:, 0] - 1).abs() * 100
    return {"day": both.index[-1].date().isoformat(), "days": int(len(both)), "max_diff_pct": float(gaps.max())}


_second_fetch = None  # tests switch the network off here


def save_second_source(result: dict | None, path: Path | None = None) -> None:
    if result is None:
        return
    import json

    path = Path(path or SECOND_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result), encoding="utf-8")


def _load_second(path: Path | None = None) -> dict | None:
    import json

    path = Path(path or SECOND_FILE)
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    except (OSError, ValueError):
        return None


# --- four bases --------------------------------------------------------------------------------


def policy_cash():
    """The research's cash series (policy rate, net of withholding), or None without the files."""

    from core.backtest.cash import load_rate_series

    if not POLICY_RATE.exists():
        return None
    return load_rate_series(POLICY_RATE, WITHHOLDING if WITHHOLDING.exists() else None)


@dataclass(frozen=True)
class FourBasis:
    nominal: float
    real: float | None
    usd: float | None
    cash: float | None
    cpi_period: str | None
    cash_note: str = "faiz yok"
    real_note: str = "TÜFE yok"

    def line(self) -> str:
        from core.reports.daily import pct

        parts = [f"nominal {pct(self.nominal)}"]
        if self.real is None:
            parts.append(f"reel: {self.real_note}")
        else:
            month = datetime.strptime(self.cpi_period, "%Y-%m")
            parts.append(f"reel {pct(self.real)} (TÜFE {month:%m.%Y}'ya kadar, tahmin yok)")
        parts.append("USD: kur yok" if self.usd is None else f"USD {pct(self.usd)}")
        parts.append(f"nakde göre: {self.cash_note}" if self.cash is None else f"nakde göre {pct(self.cash)}")
        return " · ".join(parts)


_DEFAULT = object()


def four_basis(nominal: float, start: date, end: date, cpi=_DEFAULT, usd=_DEFAULT, cash=_DEFAULT) -> FourBasis:
    cpi = load_cpi() if cpi is _DEFAULT else cpi
    usd = load_usdtry() if usd is _DEFAULT else usd
    cash = policy_cash() if cash is _DEFAULT else cash
    known = cpi_known(cpi, end) if len(cpi) else None
    real = real_return(nominal, start, end, cpi) if len(cpi) else None
    real_note = "TÜFE yok"
    if real is None and len(cpi):
        a, b = cpi_window(cpi, start, end)
        if a is not None and b is not None and b.period <= a.period:
            real_note = "dönemde yeni TÜFE yayımlanmadı"  # validation M24: not shown as real = nominal
    usd_value = usd_return(nominal, start, end, usd) if len(usd) else None
    cash_value, cash_note = None, "faiz yok"
    if cash is not None:
        growth = cash.growth(pd.Timestamp(start), pd.Timestamp(end))
        if getattr(growth, "missing_days", 0):
            cash_note = "faiz serisi dönemin başını kapsamıyor"  # never estimated (data/cash/README.md)
        else:
            cash_value = (1 + nominal) / growth.factor - 1
    return FourBasis(nominal, real, usd_value, cash_value, known.period if known and real is not None else None,
                     cash_note, real_note)


def freshness(now: date, cpi: pd.DataFrame | None = None, usd: pd.Series | None = None,
              second: dict | None | object = None, fetch: dict | None = None,
              empty: list[date] | None = None) -> tuple[str, str]:
    """(state, text) for /durum: state 'ok', 'warn' or 'unknown'."""

    cpi = load_cpi() if cpi is None else cpi
    usd = load_usdtry() if usd is None else usd
    second = _load_second() if second is None else second
    notes, state = [], "ok"
    if cpi.empty:
        return "unknown", "TÜFE dosyası yok"
    last = pd.Period(cpi.index[-1], "M")
    due = (last + 1).end_time.date() + timedelta(days=8)  # next month's figure is out by the ~3rd
    notes.append(f"TÜFE {last:%m.%Y}")
    if now > due:
        state = "warn"
        notes.append(f"{last + 1:%m.%Y} verisi eklenmedi (data/macro/cpi.csv)")
    if usd.empty:
        notes.append("kur önbelleği boş")
        state = "warn" if state == "ok" else state
    else:
        age = (pd.Timestamp(now) - usd.index[-1]).days
        notes.append(f"kur {usd.index[-1]:%d.%m.%Y}")
        if age > 5:
            state = "warn"
            notes += _stale_reasons(now, fetch, empty)
    if second:
        gap = f"{second['max_diff_pct']:.1f}".replace(".", ",")
        notes.append(f"Yahoo farkı en çok %{gap} ({second['days']} gün)")
        if second["max_diff_pct"] > SECOND_LIMIT:
            state = "warn"
    return state, ", ".join(notes)


def _stale_reasons(now: date, fetch: dict | None, empty: list[date] | None) -> list[str]:
    """Why the rate is old (03.11.2026: it stuck at 23.10 and /durum could not say why)."""

    fetch = _load_fetch() if fetch is None else fetch
    empty = _empty_days(now) if empty is None else empty
    notes = []
    if fetch:
        line = f"son deneme {date.fromisoformat(fetch['day']):%d.%m}: {fetch['asked']} bülten soruldu, {fetch['added']} eklendi"
        if fetch.get("problems"):
            line += " (" + ", ".join(f"{k}: {v}" for k, v in fetch["problems"].items()) + ")"
        notes.append(line)
    if empty:
        notes.append("boş kaydedilen gün: " + ", ".join(f"{d:%d.%m}" for d in empty))
    return notes


def main(argv: list[str] | None = None) -> int:
    from core.infrastructure.console import utf8_output

    utf8_output()
    parser = argparse.ArgumentParser(description="USD/TRY cache from TCMB bulletins; CPI file check.")
    parser.add_argument("--usd", metavar="START", help="fill the USD/TRY cache from START (YYYY-MM-DD) to today")
    parser.add_argument("--budget", type=float, default=None, help="stop after this many seconds (progress is kept)")
    parser.add_argument("--yeniden", action="store_true",
                        help="with --usd: ask again the days from START remembered without a rate")
    args = parser.parse_args(argv)
    if args.usd and args.yeniden:
        print(f"{forget_empty(date.fromisoformat(args.usd))} boş gün yeniden sorulacak")
    if args.usd:
        # the two ends first (the four-basis lines read the start and the end of a period), then the rest
        start, today = date.fromisoformat(args.usd), date.today()
        began, added = time.monotonic(), 0
        for first, last in ((today - timedelta(days=14), today), (start, start + timedelta(days=14)), (start, today)):
            left = None if args.budget is None else max(args.budget - (time.monotonic() - began), 0)
            if left == 0:
                break
            added += update_usdtry(first, last, budget=left)
        print(f"{added} gün eklendi; önbellekte {len(load_usdtry())} kur günü")
    state, text = freshness(date.today())
    print(f"Makro veri: {text} ({state})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["FourBasis", "four_basis", "freshness", "load_cpi", "load_usdtry", "parse_bulletin", "real_return",
           "update_usdtry", "usd_return"]
