"""
BIST 30 hedefi, adım 2: the ML filter. Labels are computed by hand; features of day t must not
change when the future changes (no look-ahead); a training label must be known before its test
year (purging); on a random walk the filter must stay off, and it must find a planted edge.
"""

import math
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from core.ml import features as F
from core.ml import ml_filter as M


def candles(opens, highs, lows, closes, first="2024-01-01"):
    index = pd.bdate_range(first, periods=len(closes))
    return pd.DataFrame({"open": opens, "high": highs, "low": lows, "close": closes, "volume": 1e6}, index=index)


def walk(n, seed, drift=0.0, vol=0.02, first="2015-01-01"):
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(drift, vol, n)))
    prev = np.r_[close[0], close[:-1]]
    open_ = prev * (1 + rng.normal(0, vol / 4, n))
    high = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, vol / 2, n)))
    low = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, vol / 2, n)))
    volume = rng.integers(1_000_000, 5_000_000, n).astype(float)
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume},
                        index=pd.bdate_range(first, periods=n))


class LabelTest(unittest.TestCase):
    def label(self, rows, horizon=3):
        o, h, low, c = zip(*rows, strict=True)
        return F.labels(candles(o, h, low, c), horizon=horizon)

    def test_target_first(self):
        out = self.label([(100, 100, 100, 100), (100, 101, 99.5, 100), (101, 104.5, 100, 104), (104, 105, 103, 104),
                          (104, 104, 104, 104)])
        self.assertEqual(out["label"].iloc[0], 1)  # entry 100 (next open), 104 touched on day 2
        self.assertAlmostEqual(out["r"].iloc[0], 0.04 - F.COST)
        self.assertEqual(out["label_end"].iloc[0], out.index[2])

    def test_stop_first_and_both_on_one_day_is_a_stop(self):
        out = self.label([(100, 100, 100, 100), (100, 100.5, 97.9, 99), (99, 99, 99, 99), (99, 99, 99, 99),
                          (99, 99, 99, 99)])
        self.assertEqual((out["label"].iloc[0], out["r"].iloc[0]), (0, -0.02 - F.COST))
        both = self.label([(100, 100, 100, 100), (100, 104.5, 97.5, 100), (100, 100, 100, 100),
                           (100, 100, 100, 100), (100, 100, 100, 100)])
        self.assertEqual(both["label"].iloc[0], 0)

    def test_gap_through_the_stop_fills_at_the_open(self):
        out = self.label([(100, 100, 100, 100), (100, 100, 99, 100), (95, 96, 94, 95), (95, 95, 95, 95),
                          (95, 95, 95, 95)])
        self.assertAlmostEqual(out["r"].iloc[0], 95 / 100 - 1 - F.COST)

    def test_expiry_limit_up_and_unknown_future(self):
        out = self.label([(100, 100, 100, 100), (100, 101, 99, 101), (101, 102, 100, 101), (101, 102, 100, 102),
                          (102, 102, 102, 102)])
        self.assertEqual(out["label"].iloc[0], 0)
        self.assertAlmostEqual(out["r"].iloc[0], 102 / 100 - 1 - F.COST)  # closed at the horizon
        self.assertTrue(np.isnan(out["label"].iloc[-1]))  # its future is not known yet
        limit = self.label([(100, 100, 100, 100), (110, 110, 110, 110), (110, 110, 110, 110),
                            (110, 110, 110, 110), (110, 110, 110, 110)])
        self.assertTrue(np.isnan(limit["label"].iloc[0]))  # a limit-up open: no fill


class NoLookAheadTest(unittest.TestCase):
    def test_features_of_t_ignore_the_future(self):
        df = walk(400, 1)
        before = F.features(df)
        changed = df.copy()
        changed.iloc[301:, :] *= 1.7  # rewrite everything after day 300
        changed.iloc[301:, changed.columns.get_loc("volume")] *= 5
        after = F.features(changed)
        pd.testing.assert_frame_equal(before.iloc[:301], after.iloc[:301])

    def test_training_never_sees_a_label_from_the_test_year(self):
        data = F.dataset({"A.IS": walk(1500, 2), "B.IS": walk(1500, 3)})
        start = pd.Timestamp("2019-01-01")
        train = M.train_rows(data, start)
        self.assertTrue((train["label_end"] < start).all())
        self.assertTrue((train["date"] < start).all())

    def test_holdout_is_untouched(self):
        data = F.dataset({"A.IS": walk(3200, 4)})  # runs into 2027
        seen = []

        class Spy:
            def fit(self, x, y):
                return self

            def predict_proba(self, x):
                seen.append(len(x))
                return np.tile([0.5, 0.5], (len(x), 1))

        report = M.walk_forward(data, make_model=Spy)
        self.assertNotIn(2027, [f.year for f in report.folds])
        self.assertTrue(all(f.year < 2027 for f in report.folds))
        tested = sum(f.test_rows for f in report.folds)
        self.assertEqual(tested, sum(seen))
        self.assertEqual(report.rows, int((data["date"] < M.holdout_start()).sum()))


class FilterTest(unittest.TestCase):
    def small_model(self):
        from sklearn.ensemble import RandomForestClassifier

        return RandomForestClassifier(n_estimators=40, max_depth=4, min_samples_leaf=50,
                                      class_weight="balanced_subsample", random_state=0, n_jobs=1)

    def test_random_walk_stays_off(self):
        frames = {f"S{i}.IS": walk(1800, 10 + i) for i in range(6)}
        report = M.walk_forward(F.dataset(frames), "deneme", first_year=2018, make_model=self.small_model)
        self.assertFalse(report.passed)
        self.assertIn("KAPALI", M.text(report))
        self.assertTrue(M.text(report).rstrip().endswith(M.DISCLAIMER))

    def test_a_planted_edge_is_found(self):
        # after a volume spike the next sessions rise: a real, learnable pattern
        frames = {}
        for i in range(6):
            df = walk(1800, 30 + i, vol=0.01)
            rng = np.random.default_rng(50 + i)
            spikes = rng.choice(np.arange(250, 1790), 120, replace=False)
            close = df["close"].to_numpy().copy()
            for s in sorted(spikes):
                df.iloc[s, df.columns.get_loc("volume")] *= 8
                close[s + 2:] *= 1.06
            df["close"] = close
            prev = np.r_[close[0], close[:-1]]
            df["open"] = prev
            df["high"] = np.maximum(df["open"], close) * 1.004
            df["low"] = np.minimum(df["open"], close) * 0.996
            frames[f"P{i}.IS"] = df
        report = M.walk_forward(F.dataset(frames), "deneme", first_year=2018, make_model=self.small_model)
        self.assertGreater(report.precision, report.base_rate)
        self.assertGreater(report.importances["hacim_z"], 0)

    def test_wilson_and_files(self):
        lo, hi = M.wilson(60, 100)
        self.assertAlmostEqual(lo, 0.5020, places=3)
        self.assertAlmostEqual(hi, 0.6906, places=3)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ml.json"
            self.assertFalse(M.enabled(path))
            M.save(M.Report("x", 0, passed=True, reason="eşik geçildi"), path)
            self.assertTrue(M.enabled(path))
            path.write_text("{bozuk", encoding="utf-8")
            self.assertFalse(M.enabled(path))


if __name__ == "__main__":
    unittest.main()


class LiveModelTest(unittest.TestCase):
    def test_fit_and_probabilities(self):
        from sklearn.ensemble import RandomForestClassifier

        from core.ml import live

        frames = {f"S{i}.IS": walk(900, 70 + i) for i in range(3)}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "m.joblib"
            self.assertEqual(live.probabilities(frames, path), {})  # no model yet
            cut = frames["S0.IS"].index[600].date()
            rows = live.fit(frames, today=cut, path=path,
                            make_model=lambda: RandomForestClassifier(n_estimators=10, max_depth=3, random_state=0))
            data = F.dataset(frames)
            self.assertEqual(rows, int((data["label_end"] < pd.Timestamp(cut)).sum()))  # only known labels
            proba = live.probabilities({**frames, "KISA.IS": walk(100, 9)}, path)
        self.assertEqual(sorted(proba), ["S0.IS", "S1.IS", "S2.IS"])  # too short a history is left out
        self.assertTrue(all(0 <= p <= 1 for p in proba.values()))


class RelativeRuleTest(unittest.TestCase):
    """K-62 "goreli20", written before any measurement."""

    def test_label_by_hand(self):
        n = 25
        close = np.full(n, 100.0)
        close[20] = 110.0  # stock: entry 100 (open of day 1), exit 110 at the close of day 20
        df = candles(np.full(n, 100.0), np.maximum(close, 100.0), np.full(n, 99.0), close)
        bench = pd.Series(1000.0, index=df.index)
        bench.iloc[20] = 1080.0  # XU100 +8%
        out = F.relative_labels(df, bench)
        self.assertEqual(out["label"].iloc[0], 1)  # +10% − cost beats +8%
        self.assertAlmostEqual(out["r"].iloc[0], (0.10 - F.COST) - 0.08)
        self.assertEqual(out["label_end"].iloc[0], df.index[20])
        bench.iloc[20] = 1100.0  # XU100 +10%: the cost decides
        self.assertEqual(F.relative_labels(df, bench)["label"].iloc[0], 0)
        self.assertTrue(out["label"].iloc[n - 20:].isna().all())  # the future is not known yet

    def test_limit_up_open_and_unknown_rule(self):
        df = candles([100, 110] + [110] * 22, [100, 110] + [110] * 22, [100, 110] + [110] * 22,
                     [100, 110] + [110] * 22)
        self.assertTrue(np.isnan(F.relative_labels(df, pd.Series(1000.0, index=df.index))["label"].iloc[0]))
        with self.assertRaises(ValueError):
            F.dataset({}, rule="bilinmeyen")

    def test_test_days_are_spaced_and_interval_by_dates(self):
        frames = {f"S{i}.IS": walk(1800, 90 + i) for i in range(4)}
        bench = walk(1800, 99)["close"]
        data = F.dataset(frames, rule="goreli20", bench_close=bench)
        seen = []

        class Spy:
            def fit(self, x, y):
                return self

            def predict_proba(self, x):
                seen.append(len(x))
                return np.tile([0.4, 0.6], (len(x), 1))  # every row is a signal

        report = M.walk_forward(data, "deneme", first_year=2018, make_model=Spy, rule="goreli20")
        for fold in report.folds:
            year = data[data["date"].dt.year == fold.year]
            self.assertEqual(fold.test_rows, len(year[year["date"].isin(sorted(year["date"].unique())[::20])]))
        lo, hi = report.interval
        self.assertLess(lo, report.precision)
        self.assertGreater(hi, report.precision)
        self.assertGreater(hi - lo, 2 * 1.96 * math.sqrt(0.25 / report.signals) * 0.9)  # not narrower than Wilson
        self.assertIn("goreli20", M.text(report))

    def test_random_walk_stays_off(self):
        from sklearn.ensemble import RandomForestClassifier

        frames = {f"R{i}.IS": walk(1800, 110 + i) for i in range(6)}
        data = F.dataset(frames, rule="goreli20", bench_close=walk(1800, 120)["close"])
        report = M.walk_forward(data, "deneme", first_year=2018, rule="goreli20",
                                make_model=lambda: RandomForestClassifier(n_estimators=40, max_depth=4,
                                                                          min_samples_leaf=50, random_state=0))
        self.assertFalse(report.passed)
