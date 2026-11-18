"""Experiment registry and trial counter (QB-ARS-1 §6, S-1; Faz A, 18.11.2026).

Layout under ``data/deneyler/``::

    <deney>/kayit.json          written once at registration (pre-registration, code, data digest, params)
    <deney>/sonuc_0001.json     one file per run, never overwritten
    deneme_sayaci.csv           append-only: every run adds one line; there is no reset
    butunluk.csv                append-only: sha256 of every file written here (KT-03)

Records are never changed or deleted (ANAYASA Md. 11). ``verify`` reports any changed, missing or shrunk
file. Plain JSON and CSV only (Md. 14).
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

from core.config.paths import DATA_DIR
from core.market.calendar import ISTANBUL

ROOT = DATA_DIR / "deneyler"
COUNTER = "deneme_sayaci.csv"
MANIFEST = "butunluk.csv"
RECORD = "kayit.json"
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")


class RecordExistsError(FileExistsError):
    """An experiment or result is written once; a second write is refused."""


def _now() -> datetime:
    return datetime.now(ISTANBUL)


def _check_name(name: str) -> str:
    if not NAME.match(name or "") or ".." in name:
        raise ValueError(f"geçersiz deney adı: {name!r}")
    return name


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _append(path: Path, row: list[str]) -> None:
    new = not path.exists()
    with open(path, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["yol", "sha256", "zaman"] if path.name == MANIFEST else ["zaman", "deney", "n"])
        w.writerow(row)


def _write_once(path: Path, data: dict, root: Path) -> None:
    try:
        with open(path, "x", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
    except FileExistsError as exc:
        raise RecordExistsError(str(path)) from exc
    _append(root / MANIFEST, [path.relative_to(root).as_posix(), _sha(path), _now().isoformat()])


def register(name: str, preregistration: dict, code_version: str, data_digest: str, params: dict,
             root: Path = ROOT) -> Path:
    """Create the experiment folder with its record. Refuses a second registration of the same name."""

    folder = root / _check_name(name)
    root.mkdir(parents=True, exist_ok=True)
    if folder.exists():
        raise RecordExistsError(str(folder))
    folder.mkdir()
    _write_once(folder / RECORD, {"deney": name, "on_kayit": preregistration, "kod_surumu": code_version,
                                  "veri_ozeti": data_digest, "parametreler": params,
                                  "kayit_zamani": _now().isoformat()}, root)
    return folder


def _rows(root: Path) -> list[dict]:
    path = root / COUNTER
    if not path.exists():
        return []
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def trial_count(name: str | None = None, root: Path = ROOT) -> int:
    """How many runs were recorded (all experiments, or one)."""

    return sum(1 for r in _rows(root) if name is None or r["deney"] == name)


def record_result(name: str, result: dict, root: Path = ROOT) -> int:
    """Store one run's result and count it; returns this experiment's trial number."""

    folder = root / _check_name(name)
    if not (folder / RECORD).exists():
        raise FileNotFoundError(f"kayıtlı deney yok: {name}")
    n = trial_count(name, root) + 1
    _write_once(folder / f"sonuc_{n:04d}.json", {"deney": name, "n": n, "sonuc": result,
                                                 "zaman": _now().isoformat()}, root)
    _append(root / COUNTER, [_now().isoformat(), name, str(n)])
    return n


def verify(root: Path = ROOT) -> list[str]:
    """KT-03: every file in the manifest still exists with the same hash; the counter never shrank."""

    problems: list[str] = []
    manifest = root / MANIFEST
    if not manifest.exists():
        return problems
    with open(manifest, encoding="utf-8", newline="") as f:
        entries = list(csv.DictReader(f))
    results = 0
    for e in entries:
        path = root / e["yol"]
        if not path.exists():
            problems.append(f"eksik: {e['yol']}")
        elif _sha(path) != e["sha256"]:
            problems.append(f"değişti: {e['yol']}")
        if Path(e["yol"]).name.startswith("sonuc_"):
            results += 1
    counted = trial_count(root=root)
    if counted < results:
        problems.append(f"{COUNTER}: {counted} satır, {results} sonuç dosyası (sayaç geriye gitti)")
    return problems


def summary_line(root: Path = ROOT, now: datetime | None = None) -> str:
    """The monthly report line (QB-ARS-1 §6). Validation status is added by the report, not here."""

    now = now or _now()
    month = f"{now:%Y-%m}"
    runs = sum(1 for r in _rows(root) if r["zaman"].startswith(month))
    experiments = sum(1 for p in root.glob(f"*/{RECORD}")) if root.exists() else 0
    return f"Bu ay {runs} deneme, {experiments} deney kayıtlı."
