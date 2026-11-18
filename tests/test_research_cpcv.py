"""QB-ARS-1 S-3, S-4: CPCV splits with purging and embargo, and PBO over them (Faz B, 18.11.2026).

Counts come from the definition of combinatorial purged cross-validation (López de Prado 2018, ch. 12):
N groups, k test groups -> C(N, k) splits, each group tested C(N-1, k-1) times, phi = k/N * C(N, k)
backtest paths. With N = 6, k = 2: 15 splits, 5 paths. No published PBO number could be read on
18.11.2026; PBO is checked against the existing CSCV implementation (core.backtest.overfit, K-81), which
it must equal when purge and embargo are zero and N = 16, k = 8.
"""

import math
import unittest

import numpy as np
import pandas as pd

from core.backtest import overfit
from core.research import cpcv


def noise(n_strategies, days=1600, seed=0, drift=None):
    rng = np.random.default_rng(seed)
    data = rng.normal(0.0, 0.01, size=(days, n_strategies))
    if drift is not None:
        data[:, 0] += drift
    return pd.DataFrame(data, index=pd.bdate_range("2019-01-01", periods=days),
                        columns=[f"S{i}" for i in range(n_strategies)])


class SplitCountTest(unittest.TestCase):
    def test_six_groups_two_test_give_fifteen_splits_and_five_paths(self):
        splits = cpcv.splits(600, n_groups=6, k_test=2, horizon=0, embargo=0)
        self.assertEqual(len(splits), 15)
        self.assertEqual(cpcv.n_paths(6, 2), 5)

    def test_each_group_is_tested_c_n_minus_1_k_minus_1_times(self):
        splits = cpcv.splits(600, n_groups=6, k_test=2, horizon=0, embargo=0)
        tested = np.zeros(600, dtype=int)
        for _, test in splits:
            tested[test] += 1
        self.assertTrue(np.all(tested == math.comb(5, 1)))

    def test_paths_cover_every_observation_once(self):
        paths = cpcv.paths(600, n_groups=6, k_test=2)
        self.assertEqual(len(paths), 5)
        for path in paths:
            covered = np.sort(np.concatenate([test for _, test in path]))
            self.assertTrue(np.array_equal(covered, np.arange(600)))


class NoLeakTest(unittest.TestCase):
    def test_train_and_test_never_overlap_and_stay_in_time_order(self):
        for train, test in cpcv.splits(300, n_groups=6, k_test=2, horizon=5, embargo=3):
            self.assertEqual(len(np.intersect1d(train, test)), 0)
            self.assertTrue(np.all(np.diff(train) > 0) and np.all(np.diff(test) > 0))

    def test_purge_drops_training_labels_that_reach_into_test(self):
        # groups of 100; test = group 1 (100..199) and group 3 (300..399); labels look 5 days ahead
        splits = cpcv.splits(600, n_groups=6, k_test=2, horizon=5, embargo=0)
        train, test = next((tr, te) for tr, te in splits if te[0] == 100 and 300 in te)
        for t in (95, 96, 97, 98, 99, 295, 299):
            self.assertNotIn(t, train)
        self.assertIn(94, train)
        self.assertIn(294, train)

    def test_embargo_drops_the_days_right_after_each_test_group(self):
        splits = cpcv.splits(600, n_groups=6, k_test=2, horizon=0, embargo=4)
        train, test = next((tr, te) for tr, te in splits if te[0] == 100 and 300 in te)
        for t in (200, 201, 202, 203, 400, 403):
            self.assertNotIn(t, train)
        self.assertIn(204, train)
        self.assertIn(404, train)

    def test_every_split_passes_the_leak_check(self):
        for train, test in cpcv.splits(600, n_groups=6, k_test=2, horizon=5, embargo=4):
            self.assertEqual(cpcv.leaks(train, test, horizon=5), [])

    def test_the_leak_check_catches_a_leaky_split(self):  # canary
        test = np.arange(100, 200)
        train = np.concatenate([np.arange(0, 100), np.arange(200, 600)])  # no purge: both sides leak
        self.assertEqual(cpcv.leaks(train, test, horizon=5), [95, 96, 97, 98, 99, 200, 201, 202, 203, 204])

    def test_bad_arguments_are_refused(self):
        for kwargs in ({"n_groups": 1, "k_test": 1}, {"n_groups": 6, "k_test": 0}, {"n_groups": 6, "k_test": 6},
                       {"n_groups": 6, "k_test": 2, "horizon": -1}, {"n_groups": 700, "k_test": 2}):
            with self.assertRaises(ValueError, msg=kwargs):
                cpcv.splits(600, **{"horizon": 0, "embargo": 0, **kwargs})


class PboTest(unittest.TestCase):
    def test_equals_the_existing_cscv_without_purge(self):
        for seed, drift in ((0, None), (1, 0.0006), (2, 0.003)):
            data = noise(6, seed=seed, drift=drift)
            self.assertAlmostEqual(cpcv.pbo(data, n_groups=16, k_test=8, horizon=0, embargo=0),
                                   overfit.pbo(data), places=12)

    def test_pure_noise_is_about_a_coin_toss(self):
        self.assertTrue(0.25 < cpcv.pbo(noise(10, seed=3), n_groups=10, k_test=2, horizon=5, embargo=5) < 0.75)

    def test_a_dominant_strategy_is_rarely_overfit(self):
        self.assertLess(cpcv.pbo(noise(6, drift=0.003), n_groups=10, k_test=2, horizon=5, embargo=5), 0.05)

    def test_too_few_strategies_is_none(self):
        self.assertIsNone(cpcv.pbo(noise(1), n_groups=10, k_test=2, horizon=0, embargo=0))


if __name__ == "__main__":
    unittest.main()
