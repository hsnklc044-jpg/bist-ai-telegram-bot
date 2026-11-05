"""
Faz C, M8 (support and resistance, docs/validation/M8.md). The K-49 constants are unchanged; the
code now does what K-49 says.

M8-3  a cluster spans less than its width (it used to chain: ten tops 0,45 apart became one level)
M8-5  a close-to-close jump beyond a limit move in the window is named (unrecorded corporate action)
M8-6  only a LOCKED day (one price, a limit move) makes no pivot; a big move that traded does
"""

import unittest

import numpy as np
import pandas as pd

from core.analytics import levels as L


def point(day, price, kind="tepe"):
    return L.Pivot(pd.Timestamp("2025-01-01") + pd.Timedelta(days=day), price, kind)


class ClusterSpanTest(unittest.TestCase):
    def test_chain_is_cut_at_the_width(self):
        points = [point(i, 100 + 0.45 * i) for i in range(10)]  # 100 … 104,05, steps of 0,45
        groups = L.cluster(points, 0.5)
        self.assertGreater(len(groups), 1)
        for g in groups:
            self.assertLess(max(p.price for p in g) - min(p.price for p in g), 0.5)

    def test_close_points_still_join(self):
        self.assertEqual(len(L.cluster([point(0, 100), point(1, 100.2), point(2, 100.4)], 0.5)), 1)

    def test_fast_path_agrees(self):
        rng = np.random.default_rng(3)
        c = 100 + np.cumsum(rng.normal(0, 1, 400))
        df = pd.DataFrame({"open": c, "high": c + rng.uniform(0, 1, 400), "low": c - rng.uniform(0, 1, 400),
                           "close": c}, index=pd.bdate_range("2024-01-01", periods=400))
        last = None
        for d, a, groups in L.cluster_days(df, recent=3):
            last = (d, a, groups)
        d, a, groups = last
        slow = L.cluster(L.pivots(df.iloc[max(0, d - L.LOOKBACK + 1): d + 1]), L.CLUSTER_ATR * a)
        self.assertEqual(sorted(round(p, 9) for p, _ in groups),
                         sorted(round(float(np.mean([x.price for x in g])), 9) for g in slow))


def frame_with_day(o, h, low, c, at=20, n=41):
    base = pd.DataFrame({"open": 100.0, "high": 100.5, "low": 99.5, "close": 100.0},
                        index=pd.bdate_range("2025-01-01", periods=n))
    base.iloc[at] = [o, h, low, c]
    return base


class LockedPivotTest(unittest.TestCase):
    def test_a_big_move_that_traded_can_be_a_pivot(self):
        df = frame_with_day(100, 109.6, 99.8, 109.6)  # +9,6%, traded during the day
        self.assertIn(df.index[20], [p.day for p in L.pivots(df) if p.kind == "tepe"])
        times, _ = L._pivot_arrays(df)
        self.assertIn(20, times.tolist())

    def test_a_locked_day_is_not_a_pivot(self):
        df = frame_with_day(110, 110, 110, 110)  # one price all day, +10%
        self.assertNotIn(df.index[20], [p.day for p in L.pivots(df)])
        times, _ = L._pivot_arrays(df)
        self.assertNotIn(20, times.tolist())


class JumpWarningTest(unittest.TestCase):
    def test_a_jump_is_named(self):
        rng = np.random.default_rng(1)
        c = 100 + np.cumsum(rng.normal(0, 0.5, 300))
        c[200:] = c[200:] / 2  # a 2:1 split without a record
        df = pd.DataFrame({"open": c, "high": c + 0.5, "low": c - 0.5, "close": c},
                          index=pd.bdate_range("2024-01-01", periods=300))
        text = L.levels_text("X.IS", df)
        self.assertIn("kaydı eksik bir şirket işlemi", text)

    def test_no_jump_no_warning(self):
        rng = np.random.default_rng(1)
        c = 100 + np.cumsum(rng.normal(0, 0.5, 300))
        df = pd.DataFrame({"open": c, "high": c + 0.5, "low": c - 0.5, "close": c},
                          index=pd.bdate_range("2024-01-01", periods=300))
        self.assertNotIn("şirket işlemi", L.levels_text("X.IS", df))


if __name__ == "__main__":
    unittest.main()
