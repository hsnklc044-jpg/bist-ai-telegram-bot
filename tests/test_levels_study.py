"""
Özellik A §3.3 (K-49): a descriptive measurement, not a hypothesis. When the close comes within
0.25 ATR of a cluster level, the next 5 sessions are a "dönüş" (1 ATR away in the direction it
came from), a "kırılma" (0.5 ATR through) or "belirsiz"; the same is done for random fake levels
drawn in the 52-week range. Hand-checkable outcomes; no look-ahead in the levels themselves.
"""

import unittest

import numpy as np
import pandas as pd

from core.analytics import levels_study as S


class OutcomeTest(unittest.TestCase):
    def test_support_turn_break_and_unclear(self):
        a = 2.0
        self.assertEqual(S.outcome(np.array([101, 103]), level=100, atr=a, from_above=True), "dönüş")
        self.assertEqual(S.outcome(np.array([99.5, 98.9]), level=100, atr=a, from_above=True), "kırılma")
        self.assertEqual(S.outcome(np.array([100.5, 99.5, 101.9]), level=100, atr=a, from_above=True), "belirsiz")
        self.assertEqual(S.outcome(np.array([98.9, 103]), level=100, atr=a, from_above=True), "kırılma")  # first wins

    def test_resistance_mirror(self):
        self.assertEqual(S.outcome(np.array([99, 97.5]), level=100, atr=2.0, from_above=False), "dönüş")
        self.assertEqual(S.outcome(np.array([101.1]), level=100, atr=2.0, from_above=False), "kırılma")


def bouncing(n=600, seed=0):
    """A range market: the close swings between ~100 and ~110, so real levels sit at the turns."""
    rng = np.random.default_rng(seed)
    close = 105 + 5 * np.sin(np.arange(n) * 2 * np.pi / 24) + rng.normal(0, 0.3, n)
    index = pd.bdate_range("2023-01-02", periods=n)
    return pd.DataFrame({"open": close, "high": close + 0.6, "low": close - 0.6, "close": close, "volume": 1e6},
                        index=index)


class StudyTest(unittest.TestCase):
    def test_counts_and_random_levels(self):
        df = bouncing()
        result = S.study_stock(df, rng=np.random.default_rng(1))
        self.assertGreater(result.real["n"], 5)
        self.assertGreater(result.fake["n"], 0)
        self.assertEqual(result.real["n"], result.real["dönüş"] + result.real["kırılma"] + result.real["belirsiz"])
        self.assertTrue(0 <= result.real_rate <= 1)

    def test_events_use_only_the_levels_known_that_day(self):
        df = bouncing()
        cut = 400
        before = S.study_stock(df.iloc[:cut], rng=np.random.default_rng(1), last_event=cut - 6)
        later = df.copy()
        later.iloc[cut:, :4] += 50
        after = S.study_stock(later, rng=np.random.default_rng(1), last_event=cut - 6)
        self.assertEqual(before.real, after.real)  # events before the cut see the same levels and outcomes

    def test_summary_text(self):
        frames = {"A.IS": bouncing(seed=1), "B.IS": bouncing(seed=2)}
        bench = bouncing(seed=3)
        text = S.study_text((frames, bench, None))
        self.assertIn("tanımlayıcı ölçüm", text)
        self.assertIn("rastgele", text)
        self.assertIn("dönüş", text)


if __name__ == "__main__":
    unittest.main()
