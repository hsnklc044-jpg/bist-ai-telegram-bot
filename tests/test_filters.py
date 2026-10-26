import unittest

import pandas as pd

from core.strategy.filters import apply_eligibility, eligibility
from tests.helpers import make_ohlcv


class FilterTest(unittest.TestCase):
    def test_liquidity_keeps_most_traded(self):
        frames = {f"S{i}": make_ohlcv(rows=100, seed=i) for i in range(4)}
        frames["S3"]["volume"] *= 100  # by far the most traded

        ok = eligibility(frames, liquidity_top=1)

        self.assertTrue(ok["S3"].iloc[-1])
        self.assertFalse(ok[["S0", "S1", "S2"]].iloc[-1].any())

    def test_run_up_filter(self):
        frames = {
            "CALM": make_ohlcv(rows=200, seed=1, drift=0.0, vol=0.005),
            "BUBBLE": make_ohlcv(rows=200, seed=2, drift=0.02, vol=0.005),
        }

        ok = eligibility(frames, max_run_up=1.0)

        self.assertTrue(ok["CALM"].iloc[-1])
        self.assertFalse(ok["BUBBLE"].iloc[-1])

    def test_lock_filter(self):
        df = make_ohlcv(rows=80, seed=3, vol=0.005)
        day = df.index[70]
        df.loc[day, "close"] = df["close"].iloc[69] * 0.9
        df.loc[day, ["open", "high", "low"]] = df.loc[day, "close"]

        ok = eligibility({"X": df}, max_locks=0)

        self.assertTrue(ok["X"].iloc[69])
        self.assertFalse(ok["X"].iloc[75])

    def test_no_lookahead(self):
        frames = {f"S{i}": make_ohlcv(rows=200, seed=i) for i in range(5)}
        full = eligibility(frames, liquidity_top=2, max_run_up=0.5)
        cut = eligibility({s: d.iloc[:150] for s, d in frames.items()}, liquidity_top=2, max_run_up=0.5)

        pd.testing.assert_series_equal(full.iloc[149], cut.iloc[-1], check_names=False)

    def test_apply_eligibility(self):
        idx = pd.bdate_range("2026-01-01", periods=3)
        sig = {"A": pd.DataFrame({"enter": True, "exit": False, "rank": 1.0}, index=idx)}
        ok = pd.DataFrame({"A": [True, False, True]}, index=idx)

        blocked = apply_eligibility(sig, ok)["A"]
        forced = apply_eligibility(sig, ok, exit_when_ineligible=True)["A"]

        self.assertEqual(list(blocked["enter"]), [True, False, True])
        self.assertEqual(list(blocked["exit"]), [False, False, False])
        self.assertEqual(list(forced["exit"]), [False, True, False])
