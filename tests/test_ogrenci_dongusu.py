"""
QuantBIST
K-117 (öğrenci döngüsü): the lessons ledger and the gate checklist exist, and the ledger keeps its exact
column header so that later appends cannot silently drop a column (late review, root cause, guard,
spaced re-checks). The evening review and the K-117 rules are wired into OPERATIONS and OTONOM_KURALLAR.
"""

from __future__ import annotations

import csv
import re
import unicodedata
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


def test_ders_defteri_draft_transferred_and_deneme_kopyasi_item():
    lines = _lines("DERS_DEFTERI.md")
    start = lines.index(HEADER) + 2
    rows = [r for r in lines[start:] if r.startswith("|")]
    assert len(rows) >= 15
    assert rows[13].startswith("| 21.11 | v0.99.161 (b8)")
    kapi = (DOCS / "KAPI_KONTROL_LISTESI.md").read_text(encoding="utf-8")
    assert "git'e bağımlı test .git'siz deneme kopyasında da çalışmalı" in kapi
    assert any(line.startswith("- **Onarım haftası 23–29.11.2026") for line in _lines("OPERATIONS.md"))


# K-122: aksam-tekrari kılavuzu. Sahibin şartı: kılavuzda tarih ve saat yok (bağlayıcı saat OPERATIONS'ta);
# kayda yazılan her saat o anda Get-Date ile okunur. Bulgu 13: gün sonu sinyali 23:40'tan önce yazılır.
ROOT = DOCS.parent
SKILL = ROOT / ".claude" / "skills" / "aksam-tekrari" / "SKILL.md"
_AYLAR = "Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık"
_YASAK = (
    re.compile(r"\b\d{1,2}\.\d{1,2}\.\d{4}\b"),  # 21.11.2026
    re.compile(r"\b\d{4}-\d{1,2}-\d{1,2}\b"),  # 2026-11-21
    re.compile(r"\b\d{1,2}\s*[:.]\s*\d{2}\b"),  # 23:40, 23.40, 21.11 (kısa tarih)
    re.compile(rf"\b\d{{1,2}}\s+({_AYLAR})\b", re.IGNORECASE),  # 21 Kasım
)


def tarih_saat_bul(text: str) -> list[str]:
    """Return every date or clock-time looking piece of text (NFKC first, so ':' look-alikes count)."""
    norm = unicodedata.normalize("NFKC", text)
    return [m.group(0) for pat in _YASAK for m in pat.finditer(norm)]


def _frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    assert lines[0] == "---"
    end = lines.index("---", 1)
    out = {}
    for line in lines[1:end]:
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip()
    return out


def test_tarih_saat_koruyucusu_kalibi_yakalar():
    for bad in ("21.11.2026", "2026-11-21", "23:40", "23.40", "21.11", "7:00", "23：40", "21 Kasım"):
        assert tarih_saat_bul(f"x {bad} y"), bad
    for ok in ("1, 7 ve 30 gün", "§0a", "K-117", "dört soru", "beş kez", "adım 1"):
        assert not tarih_saat_bul(ok), ok


def test_aksam_tekrari_kilavuzu_on_bilgi():
    fm = _frontmatter(SKILL.read_text(encoding="utf-8"))
    assert fm.get("name") == "aksam-tekrari"
    assert len(fm.get("description", "")) > 40


def test_aksam_tekrari_kilavuzunda_tarih_saat_yok():
    assert tarih_saat_bul(SKILL.read_text(encoding="utf-8")) == []


def test_aksam_tekrari_saatleri_get_date_ile():
    text = SKILL.read_text(encoding="utf-8")
    baslarken = text.split("## Başlarken", 1)[1].split("## ", 1)[0]
    bildir = text.split("**12. Bildir.**", 1)[1].split("## ", 1)[0]
    assert "`Get-Date`" in baslarken and "`Get-Date`" in bildir
    assert "tahmin edilmez" in text


def test_gun_sonu_sinyali_kurali_bulgu_13():
    ops = _lines("OPERATIONS.md")
    row = [line for line in ops if line.startswith("| Gün sonu sinyali (K-122) |")]
    assert len(row) == 1
    assert "23:40'tan önce" in row[0] and "doğrulama 07:00 turunda" in row[0]
    bildir = SKILL.read_text(encoding="utf-8").split("**12. Bildir.**", 1)[1]
    assert "GÜN SONU HAZIR" in bildir and "Gün sonu sinyali (K-122)" in bildir
    assert "ertelenmez" in bildir


def test_aksam_tekrari_atiflari():
    marker = "yöntem: `aksam-tekrari` kılavuzu"
    ops = _lines("OPERATIONS.md")
    assert any(line.startswith("| Akşam tekrarı (K-117) |") and marker in line for line in ops)
    assert any(line.startswith("- **Akşam tekrarı:**") and marker in line for line in ops)
    robot = (ROOT / ".claude" / "skills" / "robot" / "SKILL.md").read_text(encoding="utf-8")
    assert marker in robot


def test_k122_kayitli():
    assert "**K-122. " in (DOCS / "DECISIONS.md").read_text(encoding="utf-8")
    with (DOCS / "KARAR_DEFTERI.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    k122 = [r for r in rows if len(r) > 1 and r[1] == "K-122"]
    assert len(k122) == 1 and len(k122[0]) == len(rows[0])
