"""Decision journal (karar defteri, #13) and the N counter per hypothesis card.

`docs/KARAR_DEFTERI.csv` (UTF-8, comma) holds one row per decision that touches research: its K number in
DECISIONS, kind, card, one-sentence summary, expectation, worst case, reason, whether it adds a trial to the
card's N (`n_etkisi` 0/1) and whether it resets an incubation counter (`sayaci_sifirlar`: a rule change does,
a bug fix does not).

The journal is append-only (ANAYASA Md. 11): `append` only adds at the end, and `verify` compares the file
with an earlier committed copy: every earlier row must still be there, unchanged and in the same place. A row
is corrected by a new row, never by editing. Enforcement is a test only: tests/test_dalga1_redteam.py, run by
CI with full history, checks docs/KARAR_DEFTERI.csv against the merge-base with the bot branch (or HEAD~1).

`n_by_card` = the journal's `n_etkisi` per card + the runs core.research.experiments counted for that card
(experiment names are lowercase, so card "T1" is experiment "t1").
"""

from __future__ import annotations

import csv
import re
import subprocess
from collections import defaultdict
from datetime import date
from io import StringIO
from pathlib import Path
from typing import Iterable, Mapping

from core.research import experiments

ROOT = Path(__file__).resolve().parents[2]
JOURNAL = ROOT / "docs" / "KARAR_DEFTERI.csv"
COLUMNS = ("tarih", "karar_no", "tur", "kart", "ozet", "beklenti", "en_kotu_senaryo", "gerekce", "n_etkisi",
           "sayaci_sifirlar")
KINDS = {"esik_onayi", "kaynak_degisikligi", "kural_duzeltmesi", "hata_duzeltmesi", "kapsam", "diger"}
DECISION = re.compile(r"^K-\d+")


def check(row: Mapping) -> None:
    """Raise ValueError for a row that does not follow the journal's rules."""
    missing = [c for c in COLUMNS if c not in row]
    if missing:
        raise ValueError(f"eksik sütun {missing}")
    name = row["karar_no"] or "?"
    try:
        date.fromisoformat(row["tarih"])
    except (TypeError, ValueError):
        raise ValueError(f"{name}: tarih YYYY-AA-GG olmalı ({row['tarih']!r})") from None
    if not DECISION.match(row["karar_no"]):
        raise ValueError(f"{name}: karar_no K-xxx olmalı")
    if row["tur"] not in KINDS:
        raise ValueError(f"{name}: bilinmeyen tür {row['tur']!r}")
    if not row["ozet"].strip():
        raise ValueError(f"{name}: özet boş")
    if row["n_etkisi"] not in {"0", "1"}:
        raise ValueError(f"{name}: n_etkisi 0 ya da 1 olmalı")
    if row["sayaci_sifirlar"] not in {"evet", "hayir"}:
        raise ValueError(f"{name}: sayaci_sifirlar evet/hayir olmalı")
    if row["tur"] == "hata_duzeltmesi" and row["sayaci_sifirlar"] != "hayir":
        raise ValueError(f"{name}: hata düzeltmesi kuluçka sayacını sıfırlamaz")
    if row["tur"] == "kural_duzeltmesi" and row["sayaci_sifirlar"] != "evet":
        raise ValueError(f"{name}: kural düzeltmesi kuluçka sayacını sıfırlar")


def _parse(text: str) -> tuple[tuple[str, ...], list[dict]]:
    reader = csv.DictReader(StringIO(text))
    return tuple(reader.fieldnames or ()), list(reader)


def read(path: Path | str = JOURNAL, strict: bool = True) -> list[dict]:
    header, rows = _parse(Path(path).read_text(encoding="utf-8"))
    if strict:
        if header != COLUMNS:
            raise ValueError(f"başlık beklenenden farklı: {header}")
        for row in rows:
            check(row)
    return rows


def append(row: Mapping, path: Path | str = JOURNAL) -> None:
    """Add one checked row at the end; existing rows are never rewritten."""
    entry = {c: str(row.get(c, "")) for c in COLUMNS}
    check(entry)
    path = Path(path)
    if path.exists():
        read(path)  # a broken journal is not appended to
        text = path.read_text(encoding="utf-8")
        prefix = "" if text.endswith("\n") else "\n"
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        prefix = ",".join(COLUMNS) + "\n"
    out = StringIO()
    csv.DictWriter(out, fieldnames=COLUMNS, lineterminator="\n").writerow(entry)
    with open(path, "a", encoding="utf-8", newline="") as f:
        f.write(prefix + out.getvalue())


def _write_rows(rows: Iterable[Mapping], path: Path | str) -> None:
    """Rewrite the whole file. Tests only (to simulate an edited journal); `append` never calls it."""
    with open(path, "w", encoding="utf-8", newline="") as f:
        out = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        out.writeheader()
        out.writerows({c: r.get(c, "") for c in COLUMNS} for r in rows)


BOT_BRANCH = "origin/claude/borsa-bot-creation-n7nmc9"
UNVERIFIED = "doğrulanamadı"


def _git(*args: str) -> str | None:
    """stdout of a git command in the project; None when git is missing or the command fails."""
    try:
        got = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, timeout=30)
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    return got.stdout.decode("utf-8").replace("\r\n", "\n") if got.returncode == 0 else None


def _commit(ref: str) -> str | None:
    out = _git("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    return out.strip() or None if out else None


def base_ref(branch: str = BOT_BRANCH) -> str | None:
    """The commit to compare the journal with: the merge-base of HEAD and the bot branch when it differs from
    HEAD, otherwise HEAD~1 (on the bot branch itself, or without its ref); None without git or history."""
    head = _commit("HEAD")
    if head is None:
        return None
    if _commit(branch):
        out = _git("merge-base", "HEAD", branch)
        base = out.strip() if out else ""
        if base and base != head:
            return base
    return _commit("HEAD~1")


def committed_text(path: Path | str = JOURNAL, ref: str = "HEAD") -> str | None:
    """The journal as committed at `ref`; None without git, without that commit or when the file is not in it."""
    try:
        rel = Path(path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return None
    return _git("show", f"{ref}:{rel}")


def verify(path: Path | str = JOURNAL, base: str | None = None, ref: str = "HEAD") -> list[str]:
    """Problems when an earlier row was edited, moved or deleted, compared with `base` (a text) or, by default,
    the file as committed at `ref`. Rows added at the end are fine; a file not yet in `ref` has no earlier rows.
    Without git or without that commit the answer is one "doğrulanamadı: ..." line, never an empty list."""
    if base is None:
        if _commit(ref) is None:
            return [f"{UNVERIFIED}: git ya da {ref} yok"]
        base = committed_text(path, ref)
        if base is None:
            return []
    old_header, old = _parse(base.replace("\r\n", "\n"))
    header, rows = _parse(Path(path).read_text(encoding="utf-8"))
    if header != old_header:
        return [f"başlık değişti: {old_header} -> {header}"]
    problems = []
    for i, before in enumerate(old):
        name = f"satır {i + 1} ({before.get('karar_no', '?')})"
        if i >= len(rows):
            problems.append(f"{name} silinmiş")
        elif rows[i] != before:
            problems.append(f"{name} değiştirilmiş ya da yeri değişmiş; düzeltme yeni satırla yazılır")
    return problems


def n_by_card(path: Path | str = JOURNAL, root: Path = experiments.ROOT) -> dict[str, int]:
    """Per card in the journal: the sum of `n_etkisi` plus the experiment runs counted for that card."""
    totals: dict[str, int] = defaultdict(int)
    for row in read(path):
        if row["kart"].strip():
            totals[row["kart"].strip()] += int(row["n_etkisi"])
    return {card: n + experiments.trial_count(card.lower(), root) for card, n in totals.items()}


__all__ = ["BOT_BRANCH", "COLUMNS", "JOURNAL", "KINDS", "UNVERIFIED", "append", "base_ref", "check",
           "committed_text", "n_by_card", "read", "verify"]
