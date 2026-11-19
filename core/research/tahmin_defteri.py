"""Prediction ledger (tahmin defteri) and source scorecard (kaynak karnesi). DECISIONS K-110.

A ledger row is one dated, levelled prediction from the system or an outside source. After its
deadline a row whose `isaretleme` is `otomatik` is marked from daily CLOSES only (intraday touches
do not count):

- closes strictly after `tarih` and up to `son_tarih` (inclusive) are read in order;
- on each close the invalidation level is checked first: crossing it gives `tutmadi`
  (K-110: "önce geçersizlik gelirse tutmadı", also before the trigger);
- then the trigger (`hemen` = already triggered; `kapanis_ustu` close > level; `kapanis_alti`
  close < level); the target is checked from the trigger day itself (up: close >= target,
  down: close <= target) and gives `tuttu`;
- deadline passed without trigger: `tetiklenmedi`; triggered but target not reached: `tutmadi`;
- no close in the window although the store already reaches the deadline: `olculemez`;
- the store does not yet hold the deadline-day close and nothing was decided on the closes it has:
  the row waits (not marked).

Rows marked `elle` (non-BIST assets with no data here, or a trigger that is not a rule) and
`olculemez` rows are never touched. `gecersiz` is only set by hand.

Nothing here is a buy or sell suggestion; the ledger only records whether a stated scenario
happened. K-112: the bot runs `daily` every weekday evening. Results go to `data/tahmin_sonuclari.csv`
(untracked); the tracked ledger in docs/ is never written by the bot, so the updater is not blocked.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, Mapping

import pandas as pd

from core.infrastructure.logger import get_logger

logger = get_logger(__name__)

LEDGER = Path(__file__).resolve().parents[2] / "docs" / "TAHMIN_DEFTERI.csv"
RESULTS = Path(__file__).resolve().parents[2] / "data" / "tahmin_sonuclari.csv"
RESULT_COLUMNS = ("id", "sonuc", "sonuc_tarihi", "isaretlendi")
NOTICE = "Bu bir kayıttır; yatırım tavsiyesi değildir."

COLUMNS = (
    "id", "tarih", "kayit_turu", "kaynak", "kaynak_puani_11", "varlik", "sembol", "fiyat", "fiyat_saati",
    "metin_tetik", "metin_hedef", "metin_gecersizlik", "yon", "tetik_turu", "tetik_seviye", "hedef_seviye",
    "gecersizlik_seviye", "son_tarih", "son_tarih_kaynagi", "isaretleme", "sonuc", "sonuc_tarihi",
    "al_etiketi", "sat_etiketi", "not",
)
RESULT_VALUES = {"", "tuttu", "tutmadi", "tetiklenmedi", "gecersiz", "olculemez"}
TRIGGERS = {"hemen", "kapanis_ustu", "kapanis_alti", "elle"}
MIN_N = 10


def read(path: Path | str = LEDGER, strict: bool = True) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if strict:
        for row in rows:
            check(row)
    return rows


def write(rows: Iterable[Mapping], path: Path | str = LEDGER) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        out = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        out.writeheader()
        for row in rows:
            out.writerow({k: row.get(k, "") for k in COLUMNS})


def check(row: Mapping) -> None:
    """Raise ValueError for a row the marker could misread."""
    missing = [c for c in COLUMNS if c not in row]
    if missing:
        raise ValueError(f"{row.get('id')}: eksik sütun {missing}")
    if row["sonuc"] not in RESULT_VALUES:
        raise ValueError(f"{row['id']}: bilinmeyen sonuç {row['sonuc']!r}")
    if row["isaretleme"] not in {"otomatik", "elle", "olculemez"}:
        raise ValueError(f"{row['id']}: bilinmeyen işaretleme {row['isaretleme']!r}")
    if row["isaretleme"] != "otomatik":
        return
    if row["yon"] not in {"yukari", "asagi"}:
        raise ValueError(f"{row['id']}: otomatik satırda yön yukari/asagi olmalı")
    if row["tetik_turu"] not in TRIGGERS - {"elle"}:
        raise ValueError(f"{row['id']}: otomatik satırda tetik kurallı olmalı")
    if row["tetik_turu"] != "hemen" and not row["tetik_seviye"]:
        raise ValueError(f"{row['id']}: tetik seviyesi yok")
    if not row["hedef_seviye"] or not row["son_tarih"] or not row["sembol"]:
        raise ValueError(f"{row['id']}: hedef, son tarih ya da sembol yok")
    up = row["yon"] == "yukari"
    target = float(row["hedef_seviye"])
    if row["gecersizlik_seviye"]:
        inv = float(row["gecersizlik_seviye"])
        if (up and inv >= target) or (not up and inv <= target):
            raise ValueError(f"{row['id']}: geçersizlik hedefin yanlış tarafında")
        if row["tetik_seviye"]:
            level = float(row["tetik_seviye"])
            if (up and inv >= level) or (not up and inv <= level):
                raise ValueError(f"{row['id']}: geçersizlik tetiğin yanlış tarafında")


def _day(text: str) -> date:
    return date.fromisoformat(text)


def evaluate(row: Mapping, closes: pd.Series, today: date) -> tuple[str, str] | None:
    """(result, result date) for an automatic row whose deadline has passed; None otherwise."""
    check(row)
    if row["isaretleme"] != "otomatik" or row["sonuc"]:
        return None
    start, deadline = _day(row["tarih"]), _day(row["son_tarih"])
    if today <= deadline:
        return None
    s = closes.dropna()
    s.index = pd.to_datetime(s.index)
    if s.index.tz is not None:  # bar dates are Istanbul days
        s.index = s.index.tz_convert("Europe/Istanbul").tz_localize(None)
    complete = not s.empty and s.index.max().date() >= deadline
    window = s[(s.index.date > start) & (s.index.date <= deadline)].sort_index()
    if window.empty:
        return ("olculemez", deadline.isoformat()) if complete else None
    up = row["yon"] == "yukari"
    target = float(row["hedef_seviye"])
    inv = float(row["gecersizlik_seviye"]) if row["gecersizlik_seviye"] else None
    kind = row["tetik_turu"]
    level = float(row["tetik_seviye"]) if row["tetik_seviye"] else None
    triggered = kind == "hemen"
    for stamp, close in window.items():
        day = stamp.date().isoformat()
        if inv is not None and ((up and close < inv) or (not up and close > inv)):
            return "tutmadi", day
        if not triggered:
            triggered = (kind == "kapanis_ustu" and close > level) or (kind == "kapanis_alti" and close < level)
        if triggered and ((up and close >= target) or (not up and close <= target)):
            return "tuttu", day
    if not complete:
        return None  # a hit or a miss already seen is final; otherwise wait for the deadline-day close
    return ("tutmadi" if triggered else "tetiklenmedi"), deadline.isoformat()


def mark(rows: list[dict], closes_for, today: date, problems: list[str] | None = None) -> list[str]:
    """Mark due automatic rows in place; `closes_for(symbol)` gives a close series. Returns changed ids.

    A bad row or a symbol whose closes cannot be read is skipped and named in `problems` (when given);
    without `problems` the error is raised. One bad row never stops the others.
    """
    changed = []
    for row in rows:
        try:
            if row.get("isaretleme") != "otomatik" or row.get("sonuc") or today <= _day(row["son_tarih"]):
                continue
            got = evaluate(row, closes_for(row["sembol"]), today)
        except Exception as exc:  # noqa: BLE001 - one bad row or symbol must not stop the rest
            if problems is None:
                raise
            problems.append(f"{row.get('id', '?')}: {exc}")
            continue
        if got:
            row["sonuc"], row["sonuc_tarihi"] = got
            changed.append(row["id"])
    return changed


def _read_results(path: Path | str) -> dict[str, dict]:
    path = Path(path)
    if not path.exists():
        return {}
    with open(path, encoding="utf-8", newline="") as f:
        return {r["id"]: r for r in csv.DictReader(f)}


def read_with_results(ledger: Path | str | None = None, results: Path | str | None = None,
                      strict: bool = True) -> list[dict]:
    """Ledger rows with the bot's results applied (a result written by hand in the ledger wins)."""
    rows = read(ledger or LEDGER, strict=strict)
    results = results or RESULTS
    done = _read_results(results)
    for row in rows:
        got = done.get(row["id"])
        if got and not row["sonuc"]:
            row["sonuc"], row["sonuc_tarihi"] = got["sonuc"], got["sonuc_tarihi"]
    return rows


def daily(today: date, ledger: Path | str | None = None, results: Path | str | None = None,
          closes_for=None) -> list[str]:
    """Mark the due automatic rows; append new results to `results`. One line per newly marked row.

    A missing ledger means nothing to do (logged). Bad rows are skipped and logged, never fatal.
    """
    ledger, results = Path(ledger or LEDGER), Path(results or RESULTS)
    if not ledger.exists():
        logger.warning("Tahmin defteri yok: %s", ledger)
        return []
    rows = read_with_results(ledger, results, strict=False)
    problems: list[str] = []
    changed = mark(rows, closes_for or _store_closes, today, problems)
    for problem in problems:
        logger.warning("Tahmin defteri satırı atlandı: %s", problem)
    if not changed:
        return []
    path = results
    path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not path.exists()
    with open(path, "a", encoding="utf-8", newline="") as f:
        out = csv.DictWriter(f, fieldnames=RESULT_COLUMNS, lineterminator="\n")
        if new_file:
            out.writeheader()
        for row in rows:
            if row["id"] in changed:
                out.writerow({"id": row["id"], "sonuc": row["sonuc"], "sonuc_tarihi": row["sonuc_tarihi"],
                              "isaretlendi": today.isoformat()})
    return [f"{r['id']} ({r['varlik']}, kaynak {r['kaynak']}): {r['sonuc']}, {r['sonuc_tarihi']}"
            for r in rows if r["id"] in changed]


def message(lines: list[str]) -> str:
    return "\n".join(["📒 Tahmin defteri (K-110): süresi dolan satırlar işaretlendi", *lines, NOTICE])


@dataclass(frozen=True)
class Card:
    kaynak: str
    satir: int
    ortalama_puan: float | None
    tuttu: int
    tutmadi: int
    tetiklenmedi: int
    yon_degisimi: int

    @property
    def n(self) -> int:
        return self.tuttu + self.tutmadi

    def isabet(self) -> str:
        if self.n < MIN_N:
            return f"yetersiz örnek (N={self.n})"
        return f"%{100 * self.tuttu / self.n:.0f} (N={self.n})"


def scorecard(rows: Iterable[Mapping]) -> list[Card]:
    """Per source: mean 11-point score, hit rate (only from N >= 10), direction changes per asset."""
    by = defaultdict(list)
    for row in rows:
        by[row["kaynak"]].append(row)  # community rows get their own card too
    cards = []
    for source, items in sorted(by.items()):
        scores = [float(r["kaynak_puani_11"]) for r in items if r["kaynak_puani_11"]]
        flips = 0
        per_asset = defaultdict(list)
        for r in sorted(items, key=lambda r: (r["tarih"], r["id"])):
            if r["yon"] in {"yukari", "asagi"}:
                per_asset[r["varlik"]].append(r["yon"])
        for dirs in per_asset.values():
            flips += sum(1 for a, b in zip(dirs, dirs[1:]) if a != b)
        count = lambda v: sum(1 for r in items if r["sonuc"] == v)  # noqa: E731
        cards.append(Card(source, len(items), sum(scores) / len(scores) if scores else None,
                          count("tuttu"), count("tutmadi"), count("tetiklenmedi"), flips))
    return cards


def _store_closes(symbol: str) -> pd.Series:
    from core.market import store

    return store.read(symbol)["close"]


def main(argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(description="Tahmin defteri: süresi dolan otomatik satırları işaretle, karneyi yaz.")
    p.add_argument("--defter", default=str(LEDGER))
    p.add_argument("--isaretle", action="store_true", help="süresi dolan otomatik satırları kapanışla işaretle (sonuç data/ altına)")
    a = p.parse_args(argv)
    if a.isaretle:
        lines = daily(date.today(), Path(a.defter))
        print("işaretlenen:", "; ".join(lines) or "yok")
    rows = read_with_results(a.defter)
    for c in scorecard(rows):
        avg = "—" if c.ortalama_puan is None else f"{c.ortalama_puan:.1f}/11"
        print(f"{c.kaynak}: {c.satir} satır, puan {avg}, isabet {c.isabet()}, "
              f"tetiklenmedi {c.tetiklenmedi}, yön değişimi {c.yon_degisimi}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
