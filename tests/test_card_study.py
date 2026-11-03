"""
The card's own rule (DECISIONS K-68, written before the measurement): the outcome is the paper
book's own follow-up, a trade by hand, a random walk does not pass, the holdout is never read.
"""

import unittest
from unittest import mock

import numpy as np
import pandas as pd

from core.analytics import card_study as C


def daily(n, seed, vol=0.015, start="2018-01-02"):
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0, vol, n)))
    prev = np.r_[close[0], close[:-1]]
    open_ = prev * (1 + rng.normal(0, vol / 6, n))
    high = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, vol / 3, n)))
    low = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, vol / 3, n)))
    index = pd.bdate_range(start, periods=n)
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close,
                         "volume": rng.integers(1e5, 1e6, n).astype(float)}, index=index)


class OutcomeTest(unittest.TestCase):
    def test_trade_by_hand(self):
        # signal on day 0 (close 100); enter at 100 on day 1; day 2 high 103 lifts the stop to 100,94
        # for day 3, whose low 100,5 takes it out at 100,94 (the stop, its open 102 is above it)
        idx = pd.bdate_range("2026-01-05", periods=4)
        df = pd.DataFrame({"open": [99.0, 100, 101, 102], "high": [101.0, 101, 103, 102.5],
                           "low": [98.0, 99.5, 100.5, 100.5], "close": [100.0, 100.5, 102.5, 101]}, index=idx)
        got = C.outcome(df, 0)
        self.assertEqual(got["status"], "stop")
        self.assertAlmostEqual(got["exit_price"], 103 * 0.98)
        self.assertAlmostEqual(got["r"], 103 * 0.98 / 100 - 1 - 0.0015)

    def test_last_rows_stay_open_and_are_left_out(self):
        df = daily(300, 1)
        self.assertNotIn("r", C.outcome(df, len(df) - 3) or {"x": 1})


class StudyTest(unittest.TestCase):
    def test_random_walk_does_not_pass(self):
        frames = {f"S{i}.IS": daily(700, i) for i in range(4)}
        result = C.study(frames, before=pd.Timestamp("2026-11-02"))
        self.assertFalse(result.passed)
        self.assertIn("GEÇMEDİ", C.text(result))
        self.assertIn("hayatta kalma", C.text(result))

    def test_events_are_counted_with_the_gap(self):
        df = daily(400, 3)
        every_day = pd.Series(True, index=df.index)
        with mock.patch("core.market.extended.trigger_mask", return_value=every_day):
            picked, base = C.collect({"A.IS": df}, before=None)
        # an event every GAP+1 sessions once the indicators are warm; the baseline has every session
        self.assertTrue((picked["day"].diff().dropna() >= pd.Timedelta(days=C.GAP)).all())
        self.assertGreater(len(base), 5 * len(picked))
        self.assertTrue(set(picked["how"]) <= {"hedef", "stop", "sure"})

    def test_holdout_is_never_read(self):
        df = daily(2300, 4, start="2018-01-02")  # runs into 2026-11
        seen = []
        real = C.outcome

        def spy(frame, i, symbol=""):
            seen.append(frame.index[-1])
            return real(frame, i, symbol)

        with mock.patch.object(C, "outcome", side_effect=spy):
            C.collect({"A.IS": df}, before=pd.Timestamp("2026-11-02"))
        self.assertLess(max(seen), pd.Timestamp("2026-11-02"))

    def test_too_few_events(self):
        result = C.study({"A.IS": daily(400, 5)}, before=None)
        self.assertIn("olay", result.reason)
