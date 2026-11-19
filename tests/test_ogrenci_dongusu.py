"""
QuantBIST
K-117 (öğrenci döngüsü): the lessons ledger and the gate checklist exist, and the ledger keeps its exact
column header so that later appends cannot silently drop a column (late review, root cause, guard,
spaced re-checks). The evening review and the K-117 rules are wired into OPERATIONS and OTONOM_KURALLAR.
"""

from __future__ import annotations

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
    assert "K-117" in (DOCS / "OTONOM_KURALLAR.md").read_text(encoding="utf-8")
    ops = (DOCS / "OPERATIONS.md").read_text(encoding="utf-8")
    assert "Akşam tekrarı" in ops and "K-117" in ops
