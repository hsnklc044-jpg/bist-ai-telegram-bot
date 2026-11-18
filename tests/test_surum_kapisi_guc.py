"""Gate row 8 (18.11.2026, user's day order item 2, D.1b): on battery the install is deferred.

The 17.11 20:40 and 21:40 installs failed the speed test because the PC was on battery (Kernel-Power 105,
AcOnline=false 18:49-22:04). The gate now records the power state and stays closed unless on mains power.
"""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("surum_kapisi", ROOT / "scripts" / "surum_kapisi.py")
kapi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kapi)


def test_power_state_from_windows_ac_line_status():
    assert kapi.power_state(1) == "şebeke"
    assert kapi.power_state(0) == "pil"
    assert kapi.power_state(255) == "bilinmiyor"
    assert kapi.power_state(None) == "bilinmiyor"


def test_only_mains_power_opens_the_row():
    assert kapi.power_ok("şebeke")
    assert not kapi.power_ok("pil")
    assert not kapi.power_ok("bilinmiyor")


def test_power_state_is_recorded(tmp_path):
    log = tmp_path / "kapi_guc.csv"
    kapi.record_power(log, "2026-11-18 08:38", "3805752", "pil")
    kapi.record_power(log, "2026-11-18 20:00", "3805752", "şebeke")
    lines = log.read_text(encoding="utf-8").splitlines()
    assert lines == ["zaman,sha,guc", "2026-11-18 08:38,3805752,pil", "2026-11-18 20:00,3805752,şebeke"]
