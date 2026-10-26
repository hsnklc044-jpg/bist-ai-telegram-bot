"""
QuantBIST
BIST session clock.

Borsa Istanbul's continuous session ends at 18:00 and the closing
auction finishes a few minutes later. A daily candle is treated as
final only after SESSION_FINAL (18:15 Istanbul time). Before that,
today's candle is still moving and must not feed signals.

Holidays: data/bist_holidays.csv lists Borsa İstanbul's official full
closures and half days (eves of religious holidays and of 29 October,
when the equity market closes at about 12:40). Weekend days are not
listed. A year missing from the file is reported by /durum, and
`python -m core.market.calendar` checks the file against XU100 candles.
For history (backtests, data quality) the trading days are still
whatever days XU100 has candles for.

Source: Borsa İstanbul announcement of 4 December 2025 (2026 holidays).
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from core.config.paths import DATA_DIR

ISTANBUL = ZoneInfo("Europe/Istanbul")
SESSION_FINAL = time(18, 15)
HALF_DAY_FINAL = time(13, 15)  # half-day closing auction ends about 12:40
HOLIDAYS_FILE = DATA_DIR / "bist_holidays.csv"


@dataclass(frozen=True)
class Holiday:
    day: date
    kind: str  # "full" (closed) or "half" (morning session only)
    name: str


@lru_cache(maxsize=4)
def _load(path: str) -> dict[date, Holiday]:
    try:
        with open(path, encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
    except FileNotFoundError:
        return {}

    result = {}
    for r in rows:
        day = date.fromisoformat(r["date"])
        if r["kind"] not in ("full", "half"):
            raise ValueError(f"{path}: {r['date']} kind must be full or half, got {r['kind']!r}")
        result[day] = Holiday(day, r["kind"], r["name"])
    return result


def holidays(path: Path | str | None = None) -> dict[date, Holiday]:
    return _load(str(path or HOLIDAYS_FILE))


def holiday(day: date) -> Holiday | None:
    return holidays().get(day)


def is_session_day(day: date) -> bool:
    """A weekday that is not a full Borsa İstanbul holiday."""

    h = holiday(day)
    return day.weekday() < 5 and not (h and h.kind == "full")


def covered_until() -> int | None:
    """Last year the holiday file covers."""

    days = holidays()
    return max(days).year if days else None


def session_final(day: date) -> time:
    h = holiday(day)
    return HALF_DAY_FINAL if h and h.kind == "half" else SESSION_FINAL


def sessions_between(first: date, last: date) -> int:
    """Number of session days after `first` up to and including `last`."""

    count, day = 0, first
    while day < last:
        day += timedelta(days=1)
        count += is_session_day(day)
    return count


def now_istanbul() -> datetime:
    return datetime.now(ISTANBUL)


def last_final_session_date(now: datetime | None = None) -> date:
    """
    The most recent calendar date whose daily candle is final.

    Weekends and listed holidays roll back to the previous session; on a
    half day the candle is final after HALF_DAY_FINAL.
    """

    now = (now or now_istanbul()).astimezone(ISTANBUL)
    day = now.date()

    if not is_session_day(day) or now.time() < session_final(day):
        day -= timedelta(days=1)

    while not is_session_day(day):
        day -= timedelta(days=1)

    return day


def drop_open_candle(
    df: pd.DataFrame,
    now: datetime | None = None,
) -> pd.DataFrame:
    """Remove candles that are not final yet."""

    if df.empty:
        return df

    cutoff = pd.Timestamp(last_final_session_date(now))

    return df[df.index.normalize() <= cutoff]


def check_against_candles(candles: pd.DatetimeIndex, path: Path | str | None = None) -> list[str]:
    """
    Compare the holiday file with XU100's candles for the years it covers:
    a full holiday with a candle, or a weekday without one that is not
    listed, is reported (the second can also be a data gap).
    """

    days = holidays(path)
    if not days or candles.empty:
        return ["Tatil dosyası ya da XU100 verisi yok; karşılaştırılamadı."]

    have = {d.date() for d in candles}
    years = sorted({d.year for d in days})
    start = max(date(years[0], 1, 1), min(have))
    end = min(date(years[-1], 12, 31), max(have))

    problems = []
    for d in pd.bdate_range(start, end).date:
        h = days.get(d)
        if h and h.kind == "full" and d in have:
            problems.append(f"{d}: dosyada tatil ({h.name}) ama XU100 mumu var")
        elif not h and d not in have:
            problems.append(f"{d}: hafta içi, dosyada yok ve XU100 mumu yok (bilinmeyen tatil ya da veri boşluğu)")
        elif h and h.kind == "half" and d not in have:
            problems.append(f"{d}: yarım gün ({h.name}) ama XU100 mumu yok")
    return problems


def main(argv: list[str] | None = None) -> None:
    from core.market import store
    from core.market.universe import BENCHMARK

    parser = argparse.ArgumentParser(description="Check data/bist_holidays.csv against XU100 candles.")
    parser.parse_args(argv)

    candles = store.read(BENCHMARK).index
    problems = check_against_candles(candles)
    print(f"Tatil takvimi {min(holidays()).year}–{covered_until()} | {len(holidays())} gün")
    print("\n".join(problems) if problems else "Tatil takvimi XU100 mumlarıyla tutarlı.")


if __name__ == "__main__":
    main()


__all__ = [
    "HALF_DAY_FINAL",
    "Holiday",
    "ISTANBUL",
    "SESSION_FINAL",
    "covered_until",
    "drop_open_candle",
    "holiday",
    "holidays",
    "is_session_day",
    "last_final_session_date",
    "now_istanbul",
    "session_final",
    "sessions_between",
]
