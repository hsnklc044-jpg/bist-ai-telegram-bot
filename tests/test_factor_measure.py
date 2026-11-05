"""
K-78 measurement rules on synthetic data only (no real return is computed by these tests): holding
prices, turnover cost, the bootstrap, the verdict with its pre-written conditions and the two-download
table.
"""

import math
import unittest
from datetime import date

import numpy as np
import pandas as pd

from core.analytics import factor_measure as M


def flat(days, price=100.0):
    return pd.DataFrame({"open": price, "high": price, "low": price, "close": price, "volume": 1e6},
                        index=pd.DatetimeIndex(days))


class HoldingTest(unittest.TestCase):
    def test_entry_open_to_month_end_close(self):
        days = pd.bdate_range("2024-06-03", "2024-07-05")
        df = flat(days)
        df.loc["2024-06-03", "open"] = 100.0
        df.loc["2024-06-28", "close"] = 110.0
        got, notes = M.holding({"A": df}, ["A"], date(2024, 6, 3), pd.DatetimeIndex(days))
        self.assertAlmostEqual(got["A"], 0.10)
        self.assertEqual(notes, [])


class CostTest(unittest.TestCase):
    def test_first_month_buys_everything(self):
        self.assertAlmostEqual(M.cost(["A", "B"], []), 0.0015)

    def test_same_names_cost_nothing(self):
        self.assertEqual(M.cost(["A", "B"], ["B", "A"]), 0)

    def test_half_replaced(self):
        self.assertAlmostEqual(M.cost(["A", "C"], ["A", "B"]), 0.0015 * 0.5 + 0.0015 * 0.5)

    def test_higher_cost_line(self):
        self.assertAlmostEqual(M.cost(["A"], [], M.COST_INFO, M.COST_INFO), 0.003)


class BootstrapTest(unittest.TestCase):
    def test_same_seed_same_draws_and_length(self):
        x = np.arange(48.0)
        a, b = M.block_bootstrap(x, draws=500), M.block_bootstrap(x, draws=500)
        np.testing.assert_array_equal(a, b)
        self.assertEqual(len(a), 500)

    def test_constant_series_gives_point_interval(self):
        means = M.block_bootstrap(np.full(48, 0.01), draws=200)
        np.testing.assert_allclose(means, 0.01)


def series_of(excess, slice_net=None, universe_net=None, start="2022-11"):
    months = list(pd.period_range(start, periods=len(excess), freq="M"))
    s = M.Series(months=months, excess=list(excess), excess_high_cost=list(np.asarray(excess) - 0.001))
    s.slice_net = list(slice_net) if slice_net is not None else list(excess)
    s.universe_net = list(universe_net) if universe_net is not None else [0.0] * len(excess)
    return s


class JudgeTest(unittest.TestCase):
    rng = np.random.default_rng(1)

    def test_too_few_months_is_unmeasured(self):
        v = M.judge("momentum", series_of([0.01] * 35), draws=200)
        self.assertEqual(v.label, M.UNMEASURED)

    def test_clear_effect_passes(self):
        v = M.judge("momentum", series_of(0.02 + self.rng.normal(0, 0.01, 48)), draws=1000)
        self.assertEqual(v.label, M.PASSED, v.reasons)

    def test_tight_zero_excludes_literature_effect(self):
        v = M.judge("momentum", series_of(self.rng.normal(0, 0.002, 48)), draws=1000)
        self.assertEqual(v.label, M.EXCLUDED)
        self.assertLess(v.upper, M.LITERATURE)

    def test_wide_noise_is_unanswered(self):
        v = M.judge("momentum", series_of(self.rng.normal(0, 0.05, 48)), draws=1000)
        self.assertEqual(v.label, M.UNANSWERED)

    def test_years_condition(self):
        x = np.r_[np.full(2, 0.0), np.full(12, 0.08), np.full(12, -0.01), np.full(12, -0.01), np.full(10, 0.01)]
        v = M.judge("momentum", series_of(x), draws=1000)  # 2023 positive only
        self.assertEqual(v.years_positive, 1)
        self.assertNotEqual(v.label, M.PASSED)
        self.assertTrue(any("pozitif yıl" in r for r in v.reasons))

    def test_low_volatility_also_needs_lower_risk(self):
        x = 0.02 + self.rng.normal(0, 0.01, 48)
        calm = M.judge("dusuk_oynaklik", series_of(x, slice_net=x, universe_net=x * 3), draws=1000)
        self.assertEqual(calm.label, M.PASSED)
        wild = M.judge("dusuk_oynaklik", series_of(x, slice_net=x * 3, universe_net=x), draws=1000)
        self.assertNotEqual(wild.label, M.PASSED)
        self.assertFalse(wild.lower_risk)


class CombineTest(unittest.TestCase):
    def v(self, label):
        return M.Verdict(factor="momentum", months=48, label=label)

    def test_table(self):
        self.assertEqual(M.combine(self.v(M.PASSED), self.v(M.PASSED)), M.PASSED)
        self.assertEqual(M.combine(self.v(M.PASSED), self.v(M.UNANSWERED)), M.SENSITIVE)
        self.assertEqual(M.combine(self.v(M.EXCLUDED), self.v(M.EXCLUDED)), M.EXCLUDED)
        self.assertEqual(M.combine(self.v(M.EXCLUDED), self.v(M.UNANSWERED)), M.UNANSWERED)
        self.assertEqual(M.combine(self.v(M.UNMEASURED), self.v(M.PASSED)), M.UNMEASURED)


class SeriesTest(unittest.TestCase):
    def test_end_to_end_on_synthetic_frames(self):
        from tests.test_factor_study import bars

        frames = {f"S{i:02d}.IS": bars(n=330, end="2023-03-31", seed=i, volume=1e6 * (i + 1)) for i in range(90)}
        out = M.series(frames, lambda d: {s.removesuffix(".IS") for s in frames}, stop=pd.Timestamp("2026-11-02"))
        for k, s in out.items():
            self.assertEqual(len(s.excess), len(s.months))
            self.assertTrue(all(math.isfinite(x) for x in s.excess))
            self.assertGreaterEqual(len(s.months), 1)  # at least one valid synthetic month was measured
        self.assertIn("momentum", M.text([M.judge("momentum", out["momentum"], draws=100)]))


if __name__ == "__main__":
    unittest.main()
