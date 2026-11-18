"""Speed limit scaled by the machine's measured speed (18.11.2026, robot queue 1b; D.1b).

17.11 20:40 and 21:40 the installs failed `test_full_bist100_scan_is_fast` (10.45 s > 5 s) because the PC was
on battery (Kernel-Power 105, AcOnline=false 18:49-22:04): the CPU clock drops, and process_time stretches
with it (K-46's CPU-time guard does not cover this). The limit now grows with a fixed reference workload
measured in the same process, and never goes below the old 5 s.
"""

from tests import speed_budget as sb


def test_normal_or_faster_machine_keeps_the_old_limit():
    assert sb.scaled_limit(5.0, sb.REF_BASELINE) == 5.0
    assert sb.scaled_limit(5.0, sb.REF_BASELINE / 3) == 5.0


def test_slow_clock_scales_the_limit():
    assert sb.scaled_limit(5.0, sb.REF_BASELINE * 4) == 20.0


def test_the_17_11_battery_run_passes_but_slow_code_on_mains_still_fails():
    battery_ref = sb.REF_BASELINE * 4  # clock about 4x down: the scan's 10.45 s
    assert 10.45 < sb.scaled_limit(5.0, battery_ref)
    assert not 10.45 < sb.scaled_limit(5.0, sb.REF_BASELINE)


def test_reference_workload_is_long_enough_to_measure():
    assert sb.reference_seconds() > 0.05  # Windows process_time ticks every ~15.6 ms
