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

#12 (columns appended after the K-110 ones, order kept): `olasilik` (empty or a percentage in 5-point steps),
`referans_fiyat` (close on the publication day), `varsayim_alanlari` (fields that are our assumption, not the
source's), `cozum_kurali` (the rule that marks the row, "K-110"). At marking, besides the K-110 result and without
changing it: `yon_dogru` (did the deadline close move in the stated direction from the reference), `hep_boga`
(the always-up reference: deadline close > reference) and the TL, USD and XU100-relative returns from the
reference to the deadline close. These go to the results file; missing data leaves a field empty.

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
EXTRA_COLUMNS = ("referans_fiyat", "yon_dogru", "hep_boga", "getiri_tl", "getiri_usd", "getiri_xu100_goreli")
RESULT_COLUMNS = ("id", "sonuc", "sonuc_tarihi", "isaretlendi", *EXTRA_COLUMNS)
NOTICE = "Bu bir kayıttır; yatırım tavsiyesi değildir."

COLUMNS = (
    "id", "tarih", "kayit_turu", "kaynak", "kaynak_puani_11", "varlik", "sembol", "fiyat", "fiyat_saati",
    "metin_tetik", "metin_hedef", "metin_gecersizlik", "yon", "tetik_turu", "tetik_seviye", "hedef_seviye",
    "gecersizlik_seviye", "son_tarih", "son_tarih_kaynagi", "isaretleme", "sonuc", "sonuc_tarihi",
    "al_etiketi", "sat_etiketi", "not",
    # #12: appended, never inserted (old readers and the round trip keep the order above)
    "olasilik", "referans_fiyat", "varsayim_alanlari", "cozum_kurali", "yon_dogru", "hep_boga",
    "getiri_tl", "getiri_usd", "getiri_xu100_goreli",
)
RESULT_VALUES = {"", "tuttu", "tutmadi", "tetiklenmedi", "gecersiz", "olculemez"}
TRIGGERS = {"hemen", "kapanis_ustu", "kapanis_alti", "elle"}
MIN_N = 10
BRIER_MIN_N = 20  # #12: a Brier score only from 20 rows of a source with both a probability and a result


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
    _check_probability(row)
    unknown = [f for f in _fields(row.get("varsayim_alanlari", "")) if f not in COLUMNS]
    if unknown:
        raise ValueError(f"{row['id']}: varsayım alanı sütun değil {unknown}")
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


def _fields(text: str) -> list[str]:
    return [f.strip() for f in text.split(",") if f.strip()]


def probability(text: str) -> float | None:
    """'65' or '%65' -> 0.65; empty -> None."""
    text = text.strip().strip("%").strip()
    return float(text) / 100 if text else None


def _check_probability(row: Mapping) -> None:
    text = row.get("olasilik", "").strip().strip("%").strip()
    if not text:
        return
    if not text.isdigit() or int(text) > 100 or int(text) % 5:
        raise ValueError(f"{row['id']}: olasılık 0–100 arası, 5'in katı bir yüzde olmalı ({row['olasilik']!r})")


def _day(text: str) -> date:
    return date.fromisoformat(text)


def _istanbul_days(closes: pd.Series) -> pd.Series:
    s = closes.dropna()
    s.index = pd.to_datetime(s.index)
    if s.index.tz is not None:  # bar dates are Istanbul days
        s.index = s.index.tz_convert("Europe/Istanbul").tz_localize(None)
    return s.sort_index()


def _close_on_or_before(s: pd.Series, day: date) -> float | None:
    known = s[s.index.date <= day]
    return float(known.iloc[-1]) if len(known) else None


def _num(value: float | None, digits: int = 4) -> str:
    return "" if value is None else f"{value:.{digits}f}"


def extras(row: Mapping, closes: pd.Series, bench: pd.Series | None = None,
           usd: pd.Series | None = None) -> dict[str, str]:
    """#12 marking extras for one row; they never change the K-110 result. Missing data -> empty field.

    Reference = the ledger's `referans_fiyat`, else the last close on or before the publication day. The end is
    the close on the deadline (the series must reach the deadline). XU100-relative = TL return minus the index's
    return over the same days; USD return through the TCMB rate (core.market.macro.usd_return).
    """
    out = dict.fromkeys(EXTRA_COLUMNS, "")
    start, deadline = _day(row["tarih"]), _day(row["son_tarih"])
    s = _istanbul_days(closes)
    given = row.get("referans_fiyat", "").strip()
    ref = float(given) if given else _close_on_or_before(s, start)
    out["referans_fiyat"] = given or _num(ref, 2)
    if ref is None or ref <= 0 or s.empty or s.index.max().date() < deadline:
        return out
    end = _close_on_or_before(s, deadline)
    tl = end / ref - 1
    if row["yon"] in {"yukari", "asagi"}:
        out["yon_dogru"] = "evet" if (end > ref if row["yon"] == "yukari" else end < ref) else "hayır"
    out["hep_boga"] = "evet" if end > ref else "hayır"
    out["getiri_tl"] = _num(tl)
    if usd is not None and len(usd):
        from core.market import macro

        out["getiri_usd"] = _num(macro.usd_return(tl, start, deadline, usd))
    if bench is not None:
        b = _istanbul_days(bench)
        a = _close_on_or_before(b, start)
        if a and not b.empty and b.index.max().date() >= deadline:
            out["getiri_xu100_goreli"] = _num(tl - (_close_on_or_before(b, deadline) / a - 1))
    return out


def evaluate(row: Mapping, closes: pd.Series, today: date) -> tuple[str, str] | None:
    """(result, result date) for an automatic row whose deadline has passed; None otherwise."""
    check(row)
    if row["isaretleme"] != "otomatik" or row["sonuc"]:
        return None
    start, deadline = _day(row["tarih"]), _day(row["son_tarih"])
    if today <= deadline:
        return None
    s = _istanbul_days(closes)
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
        if not got:
            continue
        if not row["sonuc"]:
            row["sonuc"], row["sonuc_tarihi"] = got["sonuc"], got["sonuc_tarihi"]
        for c in EXTRA_COLUMNS:  # an old results file has none of them; a value in the ledger wins
            if got.get(c) and not row.get(c):
                row[c] = got[c]
    return rows


def _append_results(path: Path, new: list[dict]) -> None:
    """Append rows. A results file written before #12 (fewer columns) is first rewritten with the new header,
    its rows kept as they were and the new fields empty (the file is the bot's own, untracked)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        with open(path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            header, old = tuple(reader.fieldnames or ()), list(reader)
        if header != RESULT_COLUMNS:
            tmp = path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8", newline="") as f:
                out = csv.DictWriter(f, fieldnames=RESULT_COLUMNS, lineterminator="\n")
                out.writeheader()
                out.writerows({c: r.get(c) or "" for c in RESULT_COLUMNS} for r in old)
            tmp.replace(path)
    new_file = not path.exists()
    with open(path, "a", encoding="utf-8", newline="") as f:
        out = csv.DictWriter(f, fieldnames=RESULT_COLUMNS, lineterminator="\n")
        if new_file:
            out.writeheader()
        out.writerows(new)


def _safe(fn, *args):
    try:
        return fn(*args)
    except Exception as exc:  # noqa: BLE001 - a missing index or rate only leaves a field empty
        logger.warning("Tahmin defteri ek verisi okunamadı: %s", exc)
        return None


def daily(today: date, ledger: Path | str | None = None, results: Path | str | None = None,
          closes_for=None, usd: pd.Series | None = None) -> list[str]:
    """Mark the due automatic rows; append new results to `results`. One line per newly marked row.

    A missing ledger means nothing to do (logged). Bad rows are skipped and logged, never fatal. `usd`: the
    USD/TRY series (default: the TCMB cache, read only when a row was marked; no network).
    """
    ledger, results = Path(ledger or LEDGER), Path(results or RESULTS)
    if not ledger.exists():
        logger.warning("Tahmin defteri yok: %s", ledger)
        return []
    rows = read_with_results(ledger, results, strict=False)
    problems: list[str] = []
    closes_for = closes_for or _store_closes
    changed = mark(rows, closes_for, today, problems)
    for problem in problems:
        logger.warning("Tahmin defteri satırı atlandı: %s", problem)
    if not changed:
        return []
    from core.market.universe import BENCHMARK

    if usd is None:
        from core.market import macro

        usd = _safe(macro.load_usdtry)
    bench = _safe(closes_for, BENCHMARK)
    new = []
    for row in rows:
        if row["id"] not in changed:
            continue
        closes = _safe(closes_for, row["sembol"])
        more = (_safe(extras, row, closes, bench, usd) if closes is not None else None) or {}
        new.append({"id": row["id"], "sonuc": row["sonuc"], "sonuc_tarihi": row["sonuc_tarihi"],
                    "isaretlendi": today.isoformat(), **{c: more.get(c, "") for c in EXTRA_COLUMNS}})
    _append_results(results, new)
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
    brier_n: int = 0
    brier_toplam: float = 0.0
    yon_dogru: int = 0  # rows whose deadline close moved the stated way from the reference
    hep_boga: int = 0  # the always-up reference on the same rows: deadline close above the reference
    yon_n: int = 0

    @property
    def n(self) -> int:
        return self.tuttu + self.tutmadi

    def isabet(self) -> str:
        if self.n < MIN_N:
            return f"yetersiz örnek (N={self.n})"
        return f"%{100 * self.tuttu / self.n:.0f} (N={self.n})"

    def brier(self) -> str:
        """Mean (probability - outcome)^2 over rows with a probability and a tuttu/tutmadi result."""
        if self.brier_n < BRIER_MIN_N:
            return f"yetersiz örnek (N={self.brier_n})"
        return f"{self.brier_toplam / self.brier_n:.3f}".replace(".", ",") + f" (N={self.brier_n})"

    def yon_karsilastirma(self) -> str:
        return f"yön doğru {self.yon_dogru}/{self.yon_n}, hep boğa {self.hep_boga}/{self.yon_n}"


def scorecard(rows: Iterable[Mapping]) -> list[Card]:
    """Per source: mean 11-point score, hit rate (only from N >= 10), direction changes per asset, Brier score
    (only from 20 rows with a probability and a tuttu/tutmadi result), stated direction vs always-up counts."""
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
        scored = [(probability(r.get("olasilik", "")), r["sonuc"] == "tuttu") for r in items
                  if r.get("olasilik", "").strip() and r["sonuc"] in {"tuttu", "tutmadi"}]
        directed = [r for r in items if r.get("yon_dogru") in {"evet", "hayır"}]
        cards.append(Card(source, len(items), sum(scores) / len(scores) if scores else None,
                          count("tuttu"), count("tutmadi"), count("tetiklenmedi"), flips,
                          len(scored), sum((p - hit) ** 2 for p, hit in scored),
                          sum(r["yon_dogru"] == "evet" for r in directed),
                          sum(r.get("hep_boga") == "evet" for r in directed), len(directed)))
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
              f"tetiklenmedi {c.tetiklenmedi}, yön değişimi {c.yon_degisimi}, Brier {c.brier()}, "
              f"{c.yon_karsilastirma()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
