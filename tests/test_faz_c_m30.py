"""
Faz C, M30 (ML filter, K-59/K-62; the model is closed): the measurement method fixed before any new
measurement (DECISIONS K-77). Nothing here touches K-64 (core/ml/signal_filter.py).

M30-1  stop_hedef interval: date-block bootstrap (blocks of HORIZON sessions), not Wilson
M30-2  measurement only from the first day of the sourced membership record (point in time)
M30-3  a test row whose label ends in the holdout is not tested
M30-5  passing also needs a positive net mean, a mean above all entries and no worse loss tail;
       a 10th session locked at the lower limit exits at the first unlocked open
M30-9  /tara shows the model's output as a score, not a probability
"""

import math
import unittest

import numpy as np
import pandas as pd

from core.ml import features as F
from core.ml import ml_filter as M


def chosen_rows(days=300, stocks=20, block=10, seed=0):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2023-01-02", periods=days)
    common = np.repeat(rng.random(days // block + 1) < 0.6, block)[:days].astype(float)
    rows = [{"date": d, "symbol": f"S{s}", "label": common[i]} for i, d in enumerate(dates) for s in range(stocks)]
    return pd.DataFrame(rows)


class BlockBootstrapTest(unittest.TestCase):
    def test_overlapping_labels_widen_the_interval(self):
        rows = chosen_rows()
        lo, hi = M.block_bootstrap(rows, block=F.HORIZON)
        w_lo, w_hi = M.wilson(int(rows["label"].sum()), len(rows))
        self.assertGreater(hi - lo, 3 * (w_hi - w_lo))
        self.assertLess(lo, rows["label"].mean())
        self.assertLess(rows["label"].mean(), hi)

    def test_stop_hedef_uses_the_block_bootstrap(self):
        rows = chosen_rows()
        self.assertEqual(M.interval(rows, "stop_hedef"), M.block_bootstrap(rows, block=F.HORIZON))
        self.assertEqual(M.interval(rows, "goreli20"), M.date_bootstrap(rows))

    def test_empty(self):
        self.assertTrue(all(math.isnan(x) for x in M.block_bootstrap(chosen_rows().iloc[:0])))


def dataset_rows(start="2021-01-04", end="2026-10-30", stocks=8, seed=1):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(start, end)
    rows = []
    for s in range(stocks):
        for d in dates:
            rows.append({"date": d, "symbol": f"S{s}", "label": float(rng.random() < 0.4),
                         "r": float(rng.normal(0, 0.02)), "label_end": d + pd.Timedelta(days=14),
                         **{f: float(rng.normal()) for f in F.FEATURES}})
    return pd.DataFrame(rows)


class Everyone:
    """A model that approves every row (the test is about which rows are tested, not the model)."""

    def fit(self, x, y):
        return self

    def predict_proba(self, x):
        return np.tile([0.0, 1.0], (len(x), 1))


class TestRowsTest(unittest.TestCase):
    def test_label_ending_in_the_holdout_is_not_tested(self):
        data = dataset_rows()
        report = M.walk_forward(data, "t", first_year=2026, make_model=Everyone)
        cut = M.holdout_start()
        tested_2026 = data[(data["date"].dt.year == 2026) & (data["label_end"] < cut)]
        self.assertEqual(report.folds[-1].test_rows, len(tested_2026))

    def test_point_in_time_window(self):
        data = dataset_rows()
        start = pd.Timestamp("2022-04-01")
        kept, first_year = M.point_in_time(data, start)
        self.assertGreaterEqual(kept["date"].min(), start)
        self.assertEqual(first_year, 2023)
        report = M.walk_forward(kept, "t", first_year=first_year, make_model=Everyone)
        self.assertEqual(report.folds[0].year, 2023)

    def test_membership_record_start(self):
        self.assertEqual(M.membership_start(), pd.Timestamp("2022-04-01"))


class PassRuleTest(unittest.TestCase):
    def base(self, **kw):
        r = M.Report("t", 1000, signals=200, hits=140, precision=0.70, interval=(0.66, 0.74), base_rate=0.55,
                     mean_r_signals=0.004, mean_r_all=0.001)
        for k, v in kw.items():
            setattr(r, k, v)
        return r

    def every(self):
        return pd.DataFrame({"r": np.linspace(-0.05, 0.05, 1000)})

    def chosen(self, low=-0.03):
        return pd.DataFrame({"r": np.linspace(low, 0.05, 200)})

    def test_all_conditions_pass(self):
        r = self.base()
        M.decide(r, self.chosen(), self.every())
        self.assertTrue(r.passed, r.reason)

    def test_negative_net_mean_fails(self):
        r = self.base(mean_r_signals=-0.001)
        M.decide(r, self.chosen(), self.every())
        self.assertFalse(r.passed)
        self.assertIn("maliyet sonrası ortalama", r.reason)

    def test_mean_not_above_all_entries_fails(self):
        r = self.base(mean_r_signals=0.001, mean_r_all=0.002)
        M.decide(r, self.chosen(), self.every())
        self.assertFalse(r.passed)
        self.assertIn("tüm girişlerin ortalamasını", r.reason)

    def test_worse_loss_tail_fails(self):
        r = self.base()
        M.decide(r, self.chosen(low=-0.20), self.every())
        self.assertFalse(r.passed)
        self.assertIn("kayıp kuyruğu", r.reason)


class LockedExpiryLabelTest(unittest.TestCase):
    def test_locked_last_session_exits_at_the_next_open(self):
        rows = [[100, 100.5, 99.8, 100]] + [[100, 100.5, 99.8, 100.5]] * (F.HORIZON - 1) + [[90, 90, 90, 90]]
        rows.append([85, 86, 84, 85])
        df = pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=pd.bdate_range("2025-01-01",
                                                                                              periods=len(rows)))
        got = F.labels(df).iloc[0]
        self.assertEqual(got["label"], 0)
        self.assertAlmostEqual(got["r"], 85 / 100 - 1 - F.COST)
        self.assertEqual(got["label_end"], df.index[-1])

    def test_no_next_open_yet_means_no_label(self):
        rows = [[100, 100.5, 99.8, 100]] + [[100, 100.5, 99.8, 100.5]] * (F.HORIZON - 1) + [[90, 90, 90, 90]]
        df = pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=pd.bdate_range("2025-01-01",
                                                                                              periods=len(rows)))
        self.assertTrue(math.isnan(F.labels(df).iloc[0]["label"]))


class ScoreWordTest(unittest.TestCase):
    def test_screen_note_says_score(self):
        import inspect

        from core.screen import engine

        source = inspect.getsource(engine)
        self.assertNotIn('"ml_olasilik"', source)
        self.assertIn('"ml_skor"', source)
        self.assertIn("kalibre değil", source)


if __name__ == "__main__":
    unittest.main()
