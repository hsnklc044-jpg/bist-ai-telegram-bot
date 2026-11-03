"""
Signal confirmation layer (DECISIONS K-64, written before the measurement): labels and the
volume anomaly by hand, no look-ahead, purged folds in the outer evaluation and the
hyper-parameter search, the 0.60 decision, and no pass on a random walk.
"""

import unittest

import numpy as np
import pandas as pd

from core.ml import signal_filter as S


def daily(n, seed, vol=0.02):
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0, vol, n)))
    prev = np.r_[close[0], close[:-1]]
    open_ = prev * (1 + rng.normal(0, vol / 6, n))
    high = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, vol / 3, n)))
    low = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, vol / 3, n)))
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close,
                         "volume": rng.integers(1e6, 5e6, n).astype(float)}, index=pd.bdate_range("2018-01-01", periods=n))


class LabelFeatureTest(unittest.TestCase):
    def test_label_by_hand(self):
        idx = pd.bdate_range("2026-01-05", periods=5)
        df = pd.DataFrame({"open": [10.0, 10, 10, 10, 10], "close": [10.0, 10, 10.2, 10.4, 10]}, index=idx)
        out = S.labels(df, 2, 0.03)
        self.assertEqual(out["label"].iloc[0], 0)  # 10.2 / 10 = +2% < 3%
        self.assertEqual(out["label"].iloc[1], 1)  # 10.4 / 10 = +4%
        self.assertEqual(out["label_end"].iloc[1], idx[3])
        self.assertTrue(out["label"].iloc[3:].isna().all())  # not known yet
        limit = df.assign(open=[10.0, 11, 10, 10, 10])
        self.assertTrue(np.isnan(S.labels(limit, 2, 0.03)["label"].iloc[0]))  # limit-up open: no entry

    def test_volume_anomaly_and_no_look_ahead(self):
        df = daily(400, 1)
        f = S.features(df)
        v = df["volume"]
        self.assertAlmostEqual(f["hacim_5"].iloc[100], v.iloc[100] / v.iloc[95:100].mean() - 1)
        changed = df.copy()
        changed.iloc[300:] *= 1.8
        pd.testing.assert_frame_equal(f.iloc[:300], S.features(changed).iloc[:300])
        self.assertEqual(list(f.columns), list(S.FEATURES))


class FoldTest(unittest.TestCase):
    def test_training_labels_are_known_before_the_test(self):
        rows = S.events({f"S{i}.IS": daily(1500, 10 + i) for i in range(6)}, *S.SPEC["gunluk"])
        self.assertGreater(len(rows), 50)
        for train, test in S._purged_folds(rows, S.OUTER_CHUNKS):
            first = rows["time"].iloc[test[0]]
            self.assertTrue((rows["label_end"].iloc[train] < first).all())
            self.assertTrue((rows["time"].iloc[train] < first).all())

    def test_holdout_is_cut(self):
        df = daily(1500, 3)
        cut = df.index[1000]
        rows = S.events({"A.IS": df}, *S.SPEC["gunluk"], before=cut)
        self.assertTrue((rows["time"] < cut).all())


class ModelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = S.events({f"R{i}.IS": daily(1500, 30 + i) for i in range(40)}, *S.SPEC["gunluk"])

    def test_parameters_come_from_the_grid(self):
        model, params = S.fit(self.rows.iloc[: len(self.rows) // 2], trees=20)
        self.assertIn(params["max_depth"], S.GRID["max_depth"])
        self.assertIn(params["min_samples_leaf"], S.GRID["min_samples_leaf"])
        p, decision = S.decide(model, self.rows.iloc[[-1]])
        self.assertEqual(decision, "onaylandı" if p >= 0.60 else "yalancı sinyal")

    def test_random_walk_does_not_pass_and_accuracy_is_printed(self):
        report = S.evaluate(self.rows, "gunluk", make=lambda train: S.fit(train, trees=20))
        self.assertFalse(report.passed)
        self.assertIsNotNone(report.accuracy)
        self.assertGreater(report.tested, 200)
        text = S.text(report)
        self.assertIn("Accuracy (doğruluk):", text)
        self.assertIn("Taban oran", text)
        self.assertTrue(text.rstrip().endswith(S.DISCLAIMER))

    def test_decision_threshold(self):
        class Fixed:
            def __init__(self, p):
                self.p = p

            def predict_proba(self, x):
                return np.array([[1 - self.p, self.p]])

        row = self.rows.iloc[[0]]
        self.assertEqual(S.decide(Fixed(0.60), row)[1], "onaylandı")
        self.assertEqual(S.decide(Fixed(0.59), row)[1], "yalancı sinyal")


if __name__ == "__main__":
    unittest.main()
