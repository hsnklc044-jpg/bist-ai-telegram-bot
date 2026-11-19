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
- no close in the window: `olculemez`.

Rows marked `elle` (non-BIST assets with no data here, or a trigger that is not a rule) and
`olculemez` rows are never touched. `gecersiz` is only set by hand.

Nothing here is a buy or sell suggestion; the ledger only records whether a stated scenario
happened. The marking command is not scheduled; wiring it into the bot needs the owner's approval.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, Mapping

import pandas as pd

LEDGER = Path(__file__).resolve().parents[2] / "docs" / "TAHMIN_DEFTERI.csv"

COLUMNS = (
    "id", "tarih", "kayit_turu", "kaynak", "kaynak_puani_11", "varlik", "sembol", "fiyat", "fiyat_saati",
    "metin_tetik", "metin_hedef", "metin_gecersizlik", "yon", "tetik_turu", "tetik_seviye", "hedef_seviye",
    "gecersizlik_seviye", "son_tarih", "son_tarih_kaynagi", "isaretleme", "sonuc", "sonuc_tarihi",
    "al_etiketi", "sat_etiketi", "not",
)
RESULTS = {"", "tuttu", "tutmadi", "tetiklenmedi", "gecersiz", "olculemez"}
TRIGGERS = {"hemen", "kapanis_ustu", "kapanis_alti", "elle"}
MIN_N = 10


def read(path: Path | str = LEDGER) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
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
    if row["sonuc"] not in RESULTS:
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
    window = s[(s.index.date > start) & (s.index.date <= deadline)].sort_index()
    if window.empty:
        return "olculemez", deadline.isoformat()
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
    return ("tutmadi" if triggered else "tetiklenmedi"), deadline.isoformat()


def mark(rows: list[dict], closes_for, today: date) -> list[str]:
    """Mark due automatic rows in place; `closes_for(symbol)` gives a close series. Returns changed ids."""
    changed = []
    for row in rows:
        if row["isaretleme"] != "otomatik" or row["sonuc"] or today <= _day(row["son_tarih"]):
            continue
        got = evaluate(row, closes_for(row["sembol"]), today)
        if got:
            row["sonuc"], row["sonuc_tarihi"] = got
            changed.append(row["id"])
    return changed


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
        if row["kayit_turu"] == "tahmin":
            by[row["kaynak"]].append(row)
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
    p.add_argument("--isaretle", action="store_true", help="süresi dolan otomatik satırları kapanışla işaretle")
    a = p.parse_args(argv)
    rows = read(a.defter)
    if a.isaretle:
        changed = mark(rows, _store_closes, date.today())
        if changed:
            write(rows, a.defter)
        print("işaretlenen:", ", ".join(changed) or "yok")
    for c in scorecard(rows):
        avg = "—" if c.ortalama_puan is None else f"{c.ortalama_puan:.1f}/11"
        print(f"{c.kaynak}: {c.satir} satır, puan {avg}, isabet {c.isabet()}, "
              f"tetiklenmedi {c.tetiklenmedi}, yön değişimi {c.yon_degisimi}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
