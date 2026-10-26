import unittest

import numpy as np
import pandas as pd

from core.backtest import stats


class BootstrapTest(unittest.TestCase):
    def test_zero_mean_is_not_significant(self):
        x = pd.Series(np.tile([0.01, -0.01], 300))
        result = stats.bootstrap_excess(x)

        self.assertAlmostEqual(result.mean, 0.0)
        self.assertLess(result.low, 0)
        self.assertGreater(result.high, 0)
        self.assertEqual(result.verdict, "anlamlı değil")

    def test_clear_edge_is_significant(self):
        rng = np.random.default_rng(3)
        result = stats.bootstrap_excess(pd.Series(rng.normal(0.003, 0.01, 750)))

        self.assertTrue(result.significant)
        self.assertIn("anlamlı yüksek", result.verdict)

    def test_noise_coverage_is_close_to_the_level(self):
        rng = np.random.default_rng(7)
        hits = sum(
            (r := stats.bootstrap_excess(pd.Series(rng.normal(0, 0.02, 500)), samples=500, seed=i)).low
            < 0
            < r.high
            for i in range(100)
        )
        self.assertGreaterEqual(hits, 88)  # 95% nominal

    def test_wider_with_more_tests(self):
        rng = np.random.default_rng(5)
        x = pd.Series(rng.normal(0.001, 0.02, 600))
        one = stats.bootstrap_excess(x, level=stats.bonferroni_level(1))
        seven = stats.bootstrap_excess(x, level=stats.bonferroni_level(7))

        self.assertAlmostEqual(stats.bonferroni_level(7), 1 - 0.05 / 7)
        self.assertLess(seven.low, one.low)
        self.assertGreater(seven.high, one.high)

    def test_deterministic_and_short_series(self):
        x = pd.Series(np.random.default_rng(1).normal(0, 0.01, 300))
        self.assertEqual(stats.bootstrap_excess(x, seed=4), stats.bootstrap_excess(x, seed=4))
        self.assertIsNone(stats.bootstrap_excess(x.iloc[:30]))


class ExcessTest(unittest.TestCase):
    def test_same_days_only(self):
        days = pd.bdate_range("2026-01-01", periods=4)
        equity = pd.Series([100, 110, 121, 121.0], index=days)
        bench = pd.Series([10, 10, 11, 11.0], index=days).drop(days[2])  # missing day

        excess = stats.excess_returns(equity, bench)
        self.assertEqual(len(excess), 2)
        self.assertAlmostEqual(excess.iloc[0], 0.10)
        self.assertAlmostEqual(excess.iloc[1], 121 / 110 - 1 - 0.10)


if __name__ == "__main__":
    unittest.main()
