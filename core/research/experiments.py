"""Experiment registry and trial counter (QB-ARS-1 §6, S-1; Faz A, 18.11.2026).

Layout under ``data/deneyler/``::

    <deney>/kayit.json          written once at registration (pre-registration, code, data digest, params)
    <deney>/sonuc_0001.json     one file per run, never overwritten
    deneme_sayaci.csv           append-only: every run adds one line; there is no reset
    butunluk.csv                append-only, hash-chained: one row per file written here (KT-03)

Records are never changed or deleted (ANAYASA Md. 11). ``verify`` reports changed, missing, stray or
counter-mismatched files and a broken chain; ``head`` gives the chain's last hash, which the daily
KT-03 check keeps outside this folder, so that cutting the tail of every file at once is caught too.
Plain JSON and CSV only (Md. 14).

Red team (18.11.2026 night) hardened: the chain and outside head, stray files, per-experiment counter
check, lowercase names without Windows device names, serialisation before the file is opened.
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
NAME = re.compile(r"^[a-z0-9][a-z0-9._-]{0,79}$")
DEVICES = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(10)), *(f"lpt{i}" for i in range(10))}
GENESIS = "0" * 64
RESULT = re.compile(r"^sonuc_(\d{4})\.json$")


class RecordExistsError(FileExistsError):
    """An experiment or result is written once; a second write is refused."""


def _now() -> datetime:
    return datetime.now(ISTANBUL)


def _check_name(name: str) -> str:
    if not isinstance(name, str) or not NAME.match(name) or ".." in name or name.split(".")[0] in DEVICES:
        raise ValueError(f"geçersiz deney adı (küçük harf, rakam, . _ -; aygıt adı olamaz): {name!r}")
    return name


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _row_hash(prev: str, path: str, sha: str, when: str) -> str:
    return hashlib.sha256(f"{prev}|{path}|{sha}|{when}".encode()).hexdigest()


def _manifest(root: Path) -> list[dict]:
    path = root / MANIFEST
    if not path.exists():
        return []
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _append_manifest(root: Path, rel: str, sha: str) -> None:
    rows = _manifest(root)
    prev = rows[-1]["satir"] if rows else GENESIS
    when = _now().isoformat()
    path = root / MANIFEST
    new = not path.exists()
    with open(path, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["yol", "sha256", "zaman", "onceki", "satir"])
        w.writerow([rel, sha, when, prev, _row_hash(prev, rel, sha, when)])


def _append_counter(root: Path, name: str, n: int) -> None:
    path = root / COUNTER
    new = not path.exists()
    with open(path, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["zaman", "deney", "n"])
        w.writerow([_now().isoformat(), name, str(n)])


def _write_once(path: Path, data: dict, root: Path) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n"  # fails first
    try:
        with open(path, "x", encoding="utf-8", newline="\n") as f:
            f.write(text)
    except FileExistsError as exc:
        raise RecordExistsError(str(path)) from exc
    _append_manifest(root, path.relative_to(root).as_posix(), _sha(path))


def register(name: str, preregistration: dict, code_version: str, data_digest: str, params: dict,
             root: Path = ROOT) -> Path:
    """Create the experiment folder with its record. Refuses a second registration of the same name."""

    folder = root / _check_name(name)
    record = {"deney": name, "on_kayit": preregistration, "kod_surumu": code_version, "veri_ozeti": data_digest,
              "parametreler": params, "kayit_zamani": _now().isoformat()}
    json.dumps(record, allow_nan=False)  # refuse unstorable input before anything is created
    root.mkdir(parents=True, exist_ok=True)
    if folder.exists():
        raise RecordExistsError(str(folder))
    folder.mkdir()
    _write_once(folder / RECORD, record, root)
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
    _append_counter(root, name, n)
    return n


def head(root: Path = ROOT) -> str:
    """'<rows>:<last row hash>' of the integrity chain; kept outside this folder by the KT-03 check."""

    rows = _manifest(root)
    return f"{len(rows)}:{rows[-1]['satir'] if rows else GENESIS}"


def verify(root: Path = ROOT, expected_head: str | None = None) -> list[str]:
    """KT-03: chain intact, every listed file unchanged, no stray file, counter consistent per experiment,
    and (if given) the chain still contains the head recorded earlier outside this folder."""

    problems: list[str] = []
    if not root.exists():
        return ["kök klasör yok"] if expected_head and not expected_head.startswith("0:") else []
    entries = _manifest(root)
    on_disk = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()} - {MANIFEST, COUNTER}
    if not entries and (on_disk or (root / COUNTER).exists()):
        problems.append(f"{MANIFEST} eksik ama kayıt dosyaları var")
    prev = GENESIS
    listed: set[str] = set()
    results: dict[str, set[int]] = {}
    for i, e in enumerate(entries):
        if e.get("onceki") != prev or e.get("satir") != _row_hash(prev, e["yol"], e["sha256"], e["zaman"]):
            problems.append(f"{MANIFEST}: zincir {i + 1}. satırda kırık")
        prev = e.get("satir", "")
        listed.add(e["yol"])
        path = root / e["yol"]
        if not path.exists():
            problems.append(f"eksik: {e['yol']}")
        elif _sha(path) != e["sha256"]:
            problems.append(f"değişti: {e['yol']}")
        parts = e["yol"].split("/")
        m = RESULT.match(parts[-1]) if len(parts) == 2 else None
        if m:
            results.setdefault(parts[0], set()).add(int(m.group(1)))
    for stray in sorted(on_disk - listed):
        problems.append(f"kayıtsız dosya: {stray}")
    counted: dict[str, list[int]] = {}
    for r in _rows(root):
        counted.setdefault(r["deney"], []).append(int(r["n"]))
    for name in sorted(set(results) | set(counted)):
        got, want = counted.get(name, []), sorted(results.get(name, set()))
        if got != list(range(1, len(got) + 1)) or got != want:
            problems.append(f"{COUNTER}: {name} sayaç {got}, sonuç dosyaları {want}")
    if expected_head:
        n, _, h = expected_head.partition(":")
        if len(entries) < int(n) or (int(n) and entries[int(n) - 1].get("satir") != h):
            problems.append(f"{MANIFEST}: dışarıda saklanan baş ({expected_head[:16]}…) zincirde yok; kuyruk kesilmiş")
    return problems


def summary_line(root: Path = ROOT, now: datetime | None = None) -> str:
    """The monthly report line (QB-ARS-1 §6). Validation status is added by the report, not here."""

    now = now or _now()
    month = f"{now:%Y-%m}"
    runs = sum(1 for r in _rows(root) if r["zaman"].startswith(month))
    experiments = sum(1 for p in root.glob(f"*/{RECORD}")) if root.exists() else 0
    return f"Bu ay {runs} deneme, {experiments} deney kayıtlı."
