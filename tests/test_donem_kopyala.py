"""K-17: the Saturday SLO table also lands in docs/PERIODS/ (18.11.2026). The bot never writes docs/; the robot
copies logs/haftalik_slo/YYYY-MM-DD.txt into a branch with scripts/donem_kopyala.py."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("donem_kopyala", ROOT / "scripts" / "donem_kopyala.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_copies_each_week_once_as_markdown(tmp_path):
    src, dst = tmp_path / "logs", tmp_path / "PERIODS"
    src.mkdir()
    (src / "2026-11-14.txt").write_text("Haftalık SLO tablosu:\n✅ Rapor teslimi", encoding="utf-8")
    (src / "notlar.txt").write_text("x", encoding="utf-8")
    assert mod.copy_periods(src, dst) == ["2026-11-14.md"]
    text = (dst / "2026-11-14.md").read_text(encoding="utf-8")
    assert text.startswith("# Dönem 2026-11-14")
    assert "✅ Rapor teslimi" in text and "logs/haftalik_slo/2026-11-14.txt" in text
    assert mod.copy_periods(src, dst) == []


def test_never_overwrites_an_existing_period(tmp_path):
    src, dst = tmp_path / "logs", tmp_path / "PERIODS"
    src.mkdir()
    dst.mkdir()
    (src / "2026-11-21.txt").write_text("yeni", encoding="utf-8")
    (dst / "2026-11-21.md").write_text("eski", encoding="utf-8")
    assert mod.copy_periods(src, dst) == []
    assert (dst / "2026-11-21.md").read_text(encoding="utf-8") == "eski"


def test_missing_source_is_not_an_error(tmp_path):
    assert mod.copy_periods(tmp_path / "yok", tmp_path / "PERIODS") == []
