"""
QuantBIST
Point-in-time BIST 100 membership (survivorship-bias control).

Two inputs:
- data/bist100_changes.csv   every quarterly addition / removal since Q2 2022,
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
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from datetime import date
from pathlib import Path

import pandas as pd

from core.config.paths import DATA_DIR

CHANGES_FILE = DATA_DIR / "bist100_changes.csv"
STABLE_FILE = DATA_DIR / "bist100_stable.csv"
INDEX_SIZE = 100

# Ticker renames: old code -> code used in the price store
ALIASES = {
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


def load_changes(path: Path | str | None = None) -> dict[str, list[tuple[date, str]]]:
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
    return dict(events)


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


def load_stable(path: Path | str | None = None) -> set[str]:
    path = Path(path or STABLE_FILE)
    if not path.exists():
        raise MembershipError(
            f"{path} yok. Bugünkü resmi BIST100 listesiyle oluşturun: "
            "python -m core.market.membership --current liste.txt"
        )
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return {_code(r["symbol"]) for r in csv.DictReader(fh)}


def members_on(on: date, events=None, stable: set[str] | None = None) -> set[str]:
    events = events if events is not None else load_changes()
    stable = stable if stable is not None else load_stable()
    return stable | dynamic_members(events, on)


def check_sizes(events, stable: set[str], start: date = date(2022, 1, 3)) -> dict[date, int]:
    """Membership size on the first day and on every change date (must all be 100)."""

    days = sorted({start} | {d for ev in events.values() for d, _ in ev if d >= start})
    return {d: len(stable | dynamic_members(events, d)) for d in days}


def stable_from_current(current: list[str], events, on: date) -> set[str]:
    """Stable stocks = today's official list minus the stocks that changed since 2022."""

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


def membership_panel(index: pd.DatetimeIndex, symbols: list[str], events=None, stable=None) -> pd.DataFrame:
    """Boolean panel (dates x symbols with .IS) for apply_eligibility()."""

    events = events if events is not None else load_changes()
    stable = stable if stable is not None else load_stable()
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


def ever_members(events=None, stable=None) -> list[str]:
    """Every stock that was a BIST 100 member at some point since 2022 (with .IS)."""

    events = events if events is not None else load_changes()
    stable = stable if stable is not None else load_stable()
    return sorted(f"{s}.IS" for s in set(events) | stable)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="BIST 100 point-in-time membership")
    parser.add_argument("--current", help="text file with today's official BIST 100 tickers (any separator)")
    parser.add_argument("--on", default=None, help="date of that list (default: today)")
    args = parser.parse_args(argv)

    events = load_changes()
    if args.current:
        import re

        text = Path(args.current).read_text(encoding="utf-8-sig")
        tickers = re.findall(r"[A-ZÇĞİÖŞÜ0-9]{3,6}", text.upper())
        on = date.fromisoformat(args.on) if args.on else date.today()
        stable = stable_from_current(tickers, events, on)
        with open(STABLE_FILE, "w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh, lineterminator="\n")
            writer.writerow(["symbol", "source"])
            for s in sorted(stable):
                writer.writerow([f"{s}.IS", f"resmi BIST100 listesi {on} eksi 2022-2026 değişiklikleri"])
        print(f"Doğrulandı: her tarihte 100 üye. {len(stable)} sabit hisse {STABLE_FILE} dosyasına yazıldı.")
    stable = load_stable()
    sizes = check_sizes(events, stable)
    print(f"{len(events)} hisse değişiklik kaydında, {len(stable)} sabit hisse; "
          f"üye sayıları: {sorted(set(sizes.values()))}")
    print(f"2022'den beri üye olmuş toplam hisse: {len(ever_members(events, stable))}")


if __name__ == "__main__":
    main()
