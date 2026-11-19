"""
QuantBIST
Point-in-time BIST 100 membership (survivorship-bias control).

Two inputs:
- data/bist100_changes.csv   every quarterly addition / removal since Q4 2020,
                             one row per stock, with the Borsa İstanbul source
- data/bist100_stable.csv    the stocks that were members during the whole
                             period (never in a change row). Built once from an
                             official current list:
                                 python -m core.market.membership --current liste.txt

Membership on a date = stable stocks
                     + stocks whose last change on or before the date is "add"
                     + stocks whose first change is a later "remove" (members before it).

Checks (also run by the tests): changes alternate add/remove per stock, and the
membership has exactly 100 stocks on every date. A list that fails is refused.

Rows before COVERAGE_START (the coverage K-77 and the later pre-registrations were written on)
are opt-in: by default every function ignores them and reads the stable list as it was then,
so results equal the 2022-04 files exactly. full_history=True uses the older rows
(docs/BILESEN_GECMISI_NOTU.md).
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from core.config.paths import DATA_DIR

CHANGES_FILE = DATA_DIR / "bist100_changes.csv"
STABLE_FILE = DATA_DIR / "bist100_stable.csv"
INDEX_SIZE = 100
COVERAGE_START = date(2022, 4, 1)  # K-77: first day of the change record before it was extended back

# Ticker renames: old code -> code used in the price store
ALIASES = {
    "GUSGR": "TURSG",  # 31.08.2020 (Güneş Sigorta → Türkiye Sigorta; şirketin özel durum açıklaması), full_history only
    "EFORC": "EFOR",  # inferred: EFORC added 2025-04, EFOR removed 2026-10 (chain only consistent if same stock)
    "IPEKE": "TRENJ",  # 24.11.2025
    "KERVT": "BESLR",  # 02.06.2025 (Kerevitaş → Besler Gıda; Borsa İstanbul duyurusu, D4)
    "KOZAA": "TRMET",  # 24.11.2025
    "KOZAL": "TRALT",  # 24.11.2025
}


class MembershipError(ValueError):
    pass


def _code(symbol: str) -> str:
    code = symbol.strip().upper().removesuffix(".IS")
    return ALIASES.get(code, code)


def load_changes(path: Path | str | None = None, full_history: bool = False) -> dict[str, list[tuple[date, str]]]:
    events: dict[str, list[tuple[date, str]]] = defaultdict(list)
    with open(path or CHANGES_FILE, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            if not row.get("source", "").strip():
                raise MembershipError(f"kaynağı olmayan satır: {row}")
            events[_code(row["symbol"])].append((date.fromisoformat(row["effective_date"]), row["action"]))
    for symbol, ev in events.items():
        ev.sort()
        for (d1, a1), (d2, a2) in zip(ev, ev[1:], strict=False):
            if a1 == a2:
                raise MembershipError(f"{symbol}: {d1} ve {d2} tarihlerinde art arda '{a1}'")
    if not full_history:
        events = {s: [e for e in ev if e[0] >= COVERAGE_START] for s, ev in events.items()}
    return {s: ev for s, ev in events.items() if ev}


def dynamic_members(events: dict[str, list[tuple[date, str]]], on: date) -> set[str]:
    members = set()
    for symbol, ev in events.items():
        past = [a for d, a in ev if d <= on]
        if past:
            if past[-1] == "add":
                members.add(symbol)
        elif ev[0][1] == "remove":
            members.add(symbol)
    return members


def load_stable(
    path: Path | str | None = None, full_history: bool = False, changes_path: Path | str | None = None
) -> set[str]:
    """Stable stocks. By default also the stocks whose change rows all lie before COVERAGE_START and
    end with "add": they were members for the whole period from COVERAGE_START on."""

    path = Path(path or STABLE_FILE)
    if not path.exists():
        raise MembershipError(
            f"{path} yok. Bugünkü resmi BIST100 listesiyle oluşturun: "
            "python -m core.market.membership --current liste.txt"
        )
    with open(path, encoding="utf-8-sig", newline="") as fh:
        stable = {_code(r["symbol"]) for r in csv.DictReader(fh)}
    if not full_history:
        for symbol, ev in load_changes(changes_path, full_history=True).items():
            if ev[-1][0] < COVERAGE_START and ev[-1][1] == "add":
                stable.add(symbol)
    return stable


def members_on(on: date, events=None, stable: set[str] | None = None, full_history: bool = False) -> set[str]:
    events = events if events is not None else load_changes(full_history=full_history)
    stable = stable if stable is not None else load_stable(full_history=full_history)
    return stable | dynamic_members(events, on)


def check_sizes(events, stable: set[str], start: date | None = None) -> dict[date, int]:
    """Membership size on the first day and on every change date (must all be 100).

    The first day defaults to the day before the earliest change, so the membership
    computed for dates before any change row is checked too."""

    change_days = {d for ev in events.values() for d, _ in ev}
    if start is None:
        start = min(change_days) - timedelta(days=1)
    days = sorted({start} | {d for d in change_days if d >= start})
    return {d: len(stable | dynamic_members(events, d)) for d in days}


def stable_from_current(current: list[str], events, on: date) -> set[str]:
    """Stable stocks = today's official list minus the stocks that changed since COVERAGE_START
    (pass events loaded with full_history=True to compute the file's stable list)."""

    current_codes = {_code(s) for s in current}
    if len(current_codes) != INDEX_SIZE:
        raise MembershipError(f"liste {len(current_codes)} hisse içeriyor, {INDEX_SIZE} olmalı")
    dynamic = dynamic_members(events, on)
    missing = dynamic - current_codes
    if missing:
        raise MembershipError(
            f"değişiklik kayıtlarına göre {on} tarihinde üye olması gereken ama listede olmayan: {sorted(missing)}"
        )
    stable = current_codes - dynamic
    changed_but_absent = {s for s in current_codes - dynamic if s in events}
    if changed_but_absent:
        raise MembershipError(f"listede olup kayıtlara göre üye olmaması gereken: {sorted(changed_but_absent)}")
    sizes = check_sizes(events, stable)
    wrong = {d: n for d, n in sizes.items() if n != INDEX_SIZE}
    if wrong:
        raise MembershipError(f"üye sayısı 100 olmayan tarihler: {wrong}")
    return stable


def membership_panel(
    index: pd.DatetimeIndex, symbols: list[str], events=None, stable=None, full_history: bool = False
) -> pd.DataFrame:
    """Boolean panel (dates x symbols with .IS) for apply_eligibility()."""

    events = events if events is not None else load_changes(full_history=full_history)
    stable = stable if stable is not None else load_stable(full_history=full_history)
    change_days = sorted({d for ev in events.values() for d, _ in ev})
    out = pd.DataFrame(False, index=index, columns=symbols)
    cache: dict[date, set[str]] = {}
    for day in index:
        key = max((d for d in change_days if d <= day.date()), default=date(1900, 1, 1))
        if key not in cache:
            cache[key] = stable | dynamic_members(events, day.date())
        members = cache[key]
        out.loc[day] = [_code(s) in members for s in symbols]
    return out


def ever_members(events=None, stable=None, full_history: bool = False) -> list[str]:
    """Every stock that was a BIST 100 member at some point since COVERAGE_START (with .IS);
    full_history=True: since the change log starts (Q4 2020)."""

    events = events if events is not None else load_changes(full_history=full_history)
    stable = stable if stable is not None else load_stable(full_history=full_history)
    return sorted(f"{s}.IS" for s in set(events) | stable)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="BIST 100 point-in-time membership")
    parser.add_argument("--current", help="text file with today's official BIST 100 tickers (any separator)")
    parser.add_argument("--on", default=None, help="date of that list (default: today)")
    args = parser.parse_args(argv)

    if args.current:
        import re

        text = Path(args.current).read_text(encoding="utf-8-sig")
        tickers = re.findall(r"[A-ZÇĞİÖŞÜ0-9]{3,6}", text.upper())
        on = date.fromisoformat(args.on) if args.on else date.today()
        stable = stable_from_current(tickers, load_changes(full_history=True), on)
        with open(STABLE_FILE, "w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh, lineterminator="\n")
            writer.writerow(["symbol", "source"])
            for s in sorted(stable):
                writer.writerow([f"{s}.IS", f"resmi BIST100 listesi {on} eksi değişiklik kayıtları"])
        print(f"Doğrulandı: her tarihte 100 üye. {len(stable)} sabit hisse {STABLE_FILE} dosyasına yazıldı.")
    for full in (False, True):
        events, stable = load_changes(full_history=full), load_stable(full_history=full)
        sizes = check_sizes(events, stable)
        print(f"{'tüm geçmiş' if full else f'{COVERAGE_START} sonrası'}: {len(events)} hisse değişiklik kaydında, "
              f"{len(stable)} sabit hisse; üye sayıları: {sorted(set(sizes.values()))}; "
              f"üye olmuş toplam hisse: {len(ever_members(events, stable))}")


if __name__ == "__main__":
    main()
