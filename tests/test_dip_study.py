"""
The "dip dönüşü" study (DECISIONS K-63, written before the measurement): the forward result by
hand, the event clustering rule, a random walk does not pass, a planted effect does.
"""

import unittest

import numpy as np
import pandas as pd

from core.analytics import dip_study as D


def hourly(n, seed, vol=0.006):
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0, vol, n)))
    prev = np.r_[close[0], close[:-1]]
    open_ = prev * (1 + rng.normal(0, vol / 6, n))
    high = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, vol / 3, n)))
    low = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, vol / 3, n)))
    index = pd.date_range("2025-11-03 10:00", periods=n, freq="h", tz="Europe/Istanbul")
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close,
                         "volume": rng.integers(1e5, 1e6, n).astype(float)}, index=index)


class RulesTest(unittest.TestCase):
    def test_forward_by_hand(self):
        df = pd.DataFrame({"open": [10.0, 11, 12, 13], "close": [10.0, 11, 12, 14]})
        r = D.forward(df, 2)
        self.assertAlmostEqual(r.iloc[0], 12 / 11 - 1 - D.COST)  # enter at 11 (next open), exit at 12
        self.assertAlmostEqual(r.iloc[1], 14 / 12 - 1 - D.COST)
        self.assertTrue(r.iloc[2:].isna().all())  # the future is not known

    def test_events_are_spaced(self):
        mask = pd.Series([False, True, True, False, True, False, False, True])
        # triggers at 1, 2, 4, 7: 2 and 4 are within 3 candles of the event at 1; 7 is a new event
        self.assertEqual(list(D.events(mask, gap=3)), [False, True, False, False, False, False, False, True])

    def test_bootstrap_brackets_the_difference(self):
        days = pd.date_range("2026-01-01", periods=60, freq="D")
        rng = np.random.default_rng(0)
        picked = pd.DataFrame({"r": rng.normal(0.01, 0.02, 120), "day": np.repeat(days, 2)})
        lo, hi = D.day_bootstrap(picked, base_mean=0.0)
        self.assertLess(lo, picked["r"].mean())
        self.assertGreater(hi, picked["r"].mean())


class StudyTest(unittest.TestCase):
    END = pd.Timestamp("2030-01-01", tz="Europe/Istanbul")

    def test_random_walk_does_not_pass(self):
        frames = {f"S{i}.IS": hourly(2100, 10 + i) for i in range(10)}
        result = D.study(frames, before=self.END)
        self.assertFalse(result.passed)
        text = D.text(result)
        self.assertIn("GEÇMEDİ", text)
        self.assertTrue(text.rstrip().endswith(D.DISCLAIMER))

    def test_a_planted_rebound_passes(self):
        from core.market.extended import add_indicators, trigger_mask

        frames = {}
        for i in range(10):
            df = hourly(2100, 40 + i)
            mask = D.events(trigger_mask(add_indicators(df)))
            close = df["close"].to_numpy().copy()
            for t in np.flatnonzero(mask.to_numpy()):
                close[t + 2:] *= 1.03  # a real rebound after each trigger
            prev = np.r_[close[0], close[:-1]]
            df["close"], df["open"] = close, prev
            df["high"], df["low"] = np.maximum(prev, close) * 1.001, np.minimum(prev, close) * 0.999
            frames[f"P{i}.IS"] = df
        result = D.study(frames, before=self.END)
        self.assertGreater(result.diff, 0)
        self.assertGreater(result.interval[0], 0)

    def test_holdout_is_cut(self):
        df = hourly(2100, 5)
        cut = df.index[1500]
        picked, base = D.collect({"A.IS": df}, cut)
        self.assertTrue((base.index < cut).all())

    def test_nothing(self):
        result = D.study({}, before=self.END)
        self.assertEqual((result.events, result.passed, result.reason), (0, False, "olay yok"))


if __name__ == "__main__":
    unittest.main()
