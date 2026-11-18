"""A speed limit that follows the machine's measured speed (18.11.2026; see tests/test_speed_budget.py)."""

from __future__ import annotations

import time

import numpy as np
import pandas as pd

REF_BASELINE = 0.30  # reference_seconds() on the PC, on mains power, 18.11.2026 (0.27-0.30 s over 3 runs)


def reference_seconds() -> float:
    """CPU time of a fixed workload like the scan's (pandas windows plus plain Python), in this process."""

    frame = pd.DataFrame(np.random.default_rng(1).normal(size=(1250, 100))).cumsum()
    started = time.process_time()
    for w in (5, 10, 20, 50, 100, 200) * 5:
        frame.rolling(w).mean()
        frame.ewm(span=w).mean()
    total = 0
    for i in range(3_000_000):
        total += i * i % 7
    return time.process_time() - started


def scaled_limit(base: float, ref_seconds: float, baseline: float = REF_BASELINE) -> float:
    """`base` on a machine at least as fast as the baseline; proportionally more when the clock is slower."""

    return base * max(1.0, ref_seconds / baseline)
