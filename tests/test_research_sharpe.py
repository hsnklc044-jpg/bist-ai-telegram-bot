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


class HandComputedTest(unittest.TestCase):
    """19.11, owner's request: a value worked out by hand, independent of K-81.

    Normal returns (skew 0, raw kurtosis 3, excess 0): the denominator 1 - skew*SR + (kurt-1)/4*SR^2 becomes
    1 + SR^2/2, so PSR = Phi(SR * sqrt(T-1) / sqrt(1 + SR^2/2)).
    SR = 0.1 per period, SR* = 0, T = 101:
        sqrt(T-1) = 10;  1 + 0.01/2 = 1.005;  sqrt(1.005) = 1.0024969
        z = 0.1 * 10 / 1.0024969 = 0.9975093
        Phi(1) = 0.8413447, phi(1) = 0.2419707
        Phi(0.9975093) ~ 0.8413447 - 0.0024907 * 0.2419707 = 0.8407420 (first-order step)
        red team 19.11: exactly 0.8407413 with math.erf; the first-order step is 7e-7 off, inside places=5
    """

    def test_normal_case_by_hand(self):
        self.assertAlmostEqual(psr(0.1, 0.0, 101), 0.840742, places=5)
        self.assertAlmostEqual(excess_kurtosis_to_raw(0.0), 3.0)
        self.assertAlmostEqual(psr(0.1, 0.0, 101, skew=0.0, kurt_raw=excess_kurtosis_to_raw(0.0)), 0.840742, places=5)

    def test_values_where_the_small_terms_matter(self):
        # red team 19.11: under the null SR ~ 0, so sqrt(T) vs sqrt(T-1) and the SR^2/2 term barely move the
        # simulation. These points use a large SR and a short T, where those errors are large. Reference values
        # come from math.erf, not from NormalDist or the module, and skew/kurtosis enter by hand.
        def by_hand(sr, t, skew=0.0, kurt=3.0):
            z = sr * math.sqrt(t - 1) / math.sqrt(1 - skew * sr + (kurt - 1) / 4 * sr * sr)
            return 0.5 * (1 + math.erf(z / math.sqrt(2)))
        cases = [(0.5, 10), (0.3, 24), (1.0, 5), (0.4, 12, -1.0, 6.0), (0.2, 50, 0.5, 4.0)]
        for case in cases:
            sr, t, *rest = case
            want = by_hand(sr, t, *rest)
            self.assertAlmostEqual(psr(sr, 0.0, t, *rest), want, places=10, msg=case)
            wrong_sqrt_t = 0.5 * (1 + math.erf(sr * math.sqrt(t) / math.sqrt(1 + sr * sr / 2) / math.sqrt(2)))
            wrong_no_sr2 = 0.5 * (1 + math.erf(sr * math.sqrt(t - 1) / math.sqrt(2)))
            if not rest:  # the wrong formulas are visibly different at these points
                self.assertGreater(abs(want - wrong_sqrt_t), 1e-3, msg=case)
                self.assertGreater(abs(want - wrong_no_sr2), 1e-3, msg=case)

    def test_null_simulation_matches_the_chosen_level(self):
        # true Sharpe 0: the share PSR calls significant (PSR > 1 - alpha) is close to alpha, fixed seed
        rng = np.random.default_rng(20261119)
        reps, t = 10000, 120
        r = rng.standard_normal((reps, t))
        sr = r.mean(axis=1) / r.std(axis=1, ddof=1)
        for alpha in (0.05, 0.10):
            rate = float(np.mean([psr(s, 0.0, t) > 1 - alpha for s in sr]))
            se = math.sqrt(alpha * (1 - alpha) / reps)
            self.assertAlmostEqual(rate, alpha, delta=3.5 * se, msg=(alpha, rate))


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
