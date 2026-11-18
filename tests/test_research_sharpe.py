"""PSR / DSR checked against known truths (19.11.2026 night instruction, item 3).

The published numeric example of Bailey and López de Prado (2014) could not be read without installing a PDF
tool (no installs), so it stays in Bekleyenler. These tests use answers that are known independently:
closed-form identities, the order-statistics value E[max of 100 N(0,1)] = 2.50759 and simulation with a known
true Sharpe ratio. They also pin the module to the K-81 implementation in core/backtest/overfit.py.
"""

import math
import unittest
from statistics import NormalDist

import numpy as np
import pandas as pd

from core.backtest.overfit import deflated_sharpe
from core.research.sharpe import dsr, excess_kurtosis_to_raw, expected_max_sharpe, psr


class IdentityTest(unittest.TestCase):
    def test_equal_to_benchmark_is_one_half(self):
        self.assertAlmostEqual(psr(0.1, 0.1, 250, skew=-1.0, kurt_raw=6.0), 0.5, places=12)

    def test_normal_returns_match_lo_2002_standard_error(self):
        # skew 0, kurt 3: denominator is 1 + SR^2 / 2 (Lo, 2002)
        sr, t = 0.08, 500
        z = sr * math.sqrt(t - 1) / math.sqrt(1 + sr ** 2 / 2)
        self.assertAlmostEqual(psr(sr, 0.0, t), 0.5 * (1 + math.erf(z / math.sqrt(2))), places=12)

    def test_negative_skew_and_fat_tails_lower_the_probability(self):
        base = psr(0.1, 0.0, 250)
        self.assertLess(psr(0.1, 0.0, 250, skew=-1.0), base)
        self.assertLess(psr(0.1, 0.0, 250, kurt_raw=10.0), base)

    def test_more_trials_raise_the_bar(self):
        self.assertLess(expected_max_sharpe(1.0, 10), expected_max_sharpe(1.0, 100))
        self.assertGreater(dsr(0.1, 1000, 0.001, 10), dsr(0.1, 1000, 0.001, 1000))

    def test_zero_variance_means_no_deflation(self):
        self.assertEqual(expected_max_sharpe(0.0, 50), 0.0)
        self.assertAlmostEqual(dsr(0.05, 300, 0.0, 50), psr(0.05, 0.0, 300), places=12)


class KnownValueTest(unittest.TestCase):
    def test_expected_max_of_100_standard_normals(self):
        # exact order-statistics value E[max of 100 iid N(0,1)] = 2.50759; the approximation is within 1.5 %
        self.assertAlmostEqual(expected_max_sharpe(1.0, 100) / 2.50759, 1.0092, delta=0.002)

    def test_expected_max_coefficients_not_swapped(self):
        # red team 19.11: swapping gamma and 1 - gamma stays inside a loose tolerance; pin the value
        g, nd = 0.5772156649015329, NormalDist()
        want = (1 - g) * nd.inv_cdf(1 - 1 / 100) + g * nd.inv_cdf(1 - 1 / (100 * math.e))
        swapped = g * nd.inv_cdf(1 - 1 / 100) + (1 - g) * nd.inv_cdf(1 - 1 / (100 * math.e))
        self.assertAlmostEqual(expected_max_sharpe(1.0, 100), want, places=12)
        self.assertAlmostEqual(want, 2.5306028932, places=9)
        self.assertGreater(abs(want - swapped), 0.05)

    def test_expected_max_matches_simulation(self):
        rng = np.random.default_rng(20261119)
        for n in (20, 200):
            sim = rng.standard_normal((20000, n)).max(axis=1).mean() * 0.3
            self.assertAlmostEqual(expected_max_sharpe(0.09, n) / sim, 1.0, delta=0.03, msg=n)

    def test_psr_false_alarm_rate_is_five_percent_when_true_sharpe_is_zero(self):
        rng = np.random.default_rng(7)
        r = rng.standard_normal((4000, 250))
        sr = r.mean(axis=1) / r.std(axis=1, ddof=1)
        rate = float(np.mean([psr(s, 0.0, 250) > 0.95 for s in sr]))
        self.assertAlmostEqual(rate, 0.05, delta=0.011)  # about 3 standard errors

    def test_psr_detects_a_real_edge(self):
        rng = np.random.default_rng(11)
        r = rng.standard_normal((2000, 1000)) + 0.15  # true per-period SR 0.15
        sr = r.mean(axis=1) / r.std(axis=1, ddof=1)
        self.assertGreater(float(np.mean([psr(s, 0.0, 1000) > 0.95 for s in sr])), 0.99)


class SameAsK81Test(unittest.TestCase):
    def test_matches_overfit_deflated_sharpe(self):
        rng = np.random.default_rng(3)
        m = pd.DataFrame(rng.standard_normal((300, 8)) * 0.01 + 0.0005, columns=[f"s{i}" for i in range(8)])
        best, value, n = deflated_sharpe(m)
        sharpes = m.mean() / m.std(ddof=1)
        r = m[best].to_numpy()
        z = (r - r.mean()) / r.std()
        mine = dsr(float(sharpes[best]), len(m), float(np.var(sharpes.to_numpy(), ddof=1)), n,
                   skew=float(np.mean(z ** 3)), kurt_raw=float(np.mean(z ** 4)))
        self.assertAlmostEqual(mine, value, places=12)


class KurtosisUnitTest(unittest.TestCase):
    def test_pandas_excess_kurtosis_needs_plus_three(self):
        rng = np.random.default_rng(5)
        r = pd.Series(rng.standard_t(5, 200000))
        raw = float(((r - r.mean()) ** 4).mean() / r.var(ddof=0) ** 2)
        self.assertAlmostEqual(excess_kurtosis_to_raw(float(r.kurt())), raw, delta=0.05)
        self.assertLess(psr(0.1, 0.0, 250, kurt_raw=raw), psr(0.1, 0.0, 250, kurt_raw=float(r.kurt())))


class InputTest(unittest.TestCase):
    def test_rejects_bad_inputs(self):
        for args in [(0.1, 0.0, 1), (0.1, 0.0, 2.5), (0.1, 0.0, True), (float("nan"), 0.0, 10),
                     (0.1, 0.0, 10, 0.0, 0.5), ("0.1", 0.0, 10)]:
            with self.assertRaises(ValueError, msg=args):
                psr(*args)
        with self.assertRaises(ValueError):
            psr(0.1, 0.0, 100, skew=2.0, kurt_raw=1.5)  # impossible: kurt < 1 + skew^2 (red team 19.11)
        for args in [(1e160, 0.0, 10), (0.1, 0.0, 10 ** 400)]:  # overflow becomes ValueError
            with self.assertRaises(ValueError, msg=args):
                psr(*args)
        for args in [(-1.0, 10), (1.0, 1), (1.0, 2.0), (1.0, True), (1.0, 2 ** 60)]:
            with self.assertRaises(ValueError, msg=args):
                expected_max_sharpe(*args)


if __name__ == "__main__":
    unittest.main()
