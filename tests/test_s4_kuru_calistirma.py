"""S4 dry run (18.11.2026, day order item 4): the live first-decision path end to end on fake data."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("s4_kuru", ROOT / "scripts" / "s4_kuru_calistirma.py")
kuru = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kuru)


def test_end_to_end_writes_decision_draft_drift_reasons_and_notice_once(tmp_path):
    r = kuru.dry_run(tmp_path)
    assert len(r["messages"]) == 2 and r["second"] == []
    assert r["messages"][0].startswith("📏 S4 canlı ölçüm: ilk karar")
    assert r["messages"][1].startswith("🔔 Kural anlamlı çıktı")
    assert len(r["decision"]["views"]) == 5
    strong = next(v for v in r["decision"]["views"] if v["view"] == kuru.STRONG)
    assert "sapma" in strong["drift"] and strong["reasons"]
    assert r["notice"]["views"][0]["view"] == kuru.STRONG
    assert "## 06.01.2027 – Canlı ölçüm ilk kararı (K-93)" in r["draft"] and "neden?" in r["draft"]
    assert r["draft_files"] == ["2027-01-06_canli_ilk_karar.md"]


def test_markdown_says_fake_data(tmp_path):
    text = kuru.markdown(kuru.dry_run(tmp_path))
    assert "SAHTE VERİ" in text and "Bu bir ölçüm değildir" in text
