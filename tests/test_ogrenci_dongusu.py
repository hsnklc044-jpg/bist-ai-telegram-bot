"""
QuantBIST
K-117 (öğrenci döngüsü): the lessons ledger and the gate checklist exist, and the ledger keeps its exact
column header so that later appends cannot silently drop a column (late review, root cause, guard,
spaced re-checks). The evening review and the K-117 rules are wired into OPERATIONS and OTONOM_KURALLAR.
"""

from __future__ import annotations

import csv
from pathlib import Path

DOCS = Path(__file__).resolve().parents[1] / "docs"
HEADER = (
    "| tarih | bulgu | önem | kök neden (5 neden özeti) | düzeltme | koruma | ders | kontrol maddesi "
    "| yeniden kontrol (1/7/30 gün) | durum |"
)


def _lines(name: str) -> list[str]:
    return (DOCS / name).read_text(encoding="utf-8").splitlines()


def test_ders_defteri_has_exact_header_once():
    lines = _lines("DERS_DEFTERI.md")
    assert lines.count(HEADER) == 1
    separator = lines[lines.index(HEADER) + 1]
    assert separator.count("|") == HEADER.count("|")
    assert set(separator.replace("|", "").replace(" ", "")) == {"-"}


def test_ders_defteri_rows_keep_column_count():
    lines = _lines("DERS_DEFTERI.md")
    start = lines.index(HEADER) + 2
    for row in lines[start:]:
        if row.startswith("|"):
            assert row.count("|") == HEADER.count("|"), row


def test_kapi_kontrol_listesi_exists():
    text = (DOCS / "KAPI_KONTROL_LISTESI.md").read_text(encoding="utf-8")
    assert "K-117" in text


def test_k117_wired_into_rules_and_hours():
    assert "## Öğrenci döngüsü (K-117)" in _lines("OTONOM_KURALLAR.md")
    ops = _lines("OPERATIONS.md")
    assert "### 0a. Öğrenci döngüsü (K-117, 19.11.2026)" in ops
    assert any(line.startswith("| Akşam tekrarı (K-117) |") for line in ops)


def test_k117_karar_defteri_row():
    with (DOCS / "KARAR_DEFTERI.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    k117 = [r for r in rows if len(r) > 1 and r[1] == "K-117"]
    assert len(k117) == 1 and len(k117[0]) == len(rows[0]) == 10
