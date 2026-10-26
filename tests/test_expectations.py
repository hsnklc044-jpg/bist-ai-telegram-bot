"""The live reference must score past days exactly as /performans scores live records."""

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from core.backtest import expectations
from core.reports.forward import forward_excess
from core.strategy.score import score_frame
from tests.helpers import make_ohlcv


class ViewExcessTest(unittest.TestCase):
    def setUp(self):
        self.stock = make_ohlcv(rows=300, seed=3)
        self.bench = make_ohlcv(rows=300, seed=9, vol=0.01)

    def test_matches_live_scoring_day_by_day(self):
        rows = expectations.view_excess(self.stock, self.bench, horizons=(5, 20))
        self.assertFalse(rows.empty)
        sample = rows.iloc[:: max(1, len(rows) // 40)]
        for r in sample.itertuples():
            live = forward_excess(self.stock, self.bench, r.day.date(), r.horizon)
            self.assertIsNotNone(live)
            self.assertAlmostEqual(r.excess, live, places=12)

    def test_no_row_before_the_outcome_exists_or_without_a_score(self):
        rows = expectations.view_excess(self.stock, self.bench, horizons=(20,))
        self.assertLessEqual(rows["day"].max(), self.stock.index[-21])
        scored = score_frame(self.stock)["score"].dropna().index
        self.assertTrue(set(rows["day"]) <= set(scored))

    def test_view_uses_only_the_past(self):
        # changing prices after a day must not change that day's view
        rows = expectations.view_excess(self.stock, self.bench, horizons=(5,))
        changed = self.stock.copy()
        changed.iloc[-50:, :4] *= 1.7
        later = expectations.view_excess(changed, self.bench, horizons=(5,))
        cut = self.stock.index[-50]
        a = rows[rows["day"] < cut].set_index("day")["view"]
        b = later[later["day"] < cut].set_index("day")["view"]
        pd.testing.assert_series_equal(a, b)

    def test_membership_and_period(self):
        frames = {"A.IS": self.stock, "B.IS": make_ohlcv(rows=300, seed=4)}
        eligible = pd.DataFrame(True, index=self.stock.index, columns=["A.IS", "B.IS"])
        eligible.loc[:, "B.IS"] = False
        start = str(self.stock.index[150].date())
        table = expectations.expectations(frames, self.bench, eligible, start=start, horizons=(5,))
        only_a = expectations.expectations({"A.IS": self.stock}, self.bench, None, start=start, horizons=(5,))
        pd.testing.assert_frame_equal(table.reset_index(drop=True), only_a.reset_index(drop=True))
        self.assertTrue((table["period_start"] >= start).all())

    def test_write_and_load(self):
        table = expectations.expectations({"A.IS": self.stock}, self.bench, horizons=(5, 20))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "exp.csv"
            expectations.write(table, path, "pit")
            loaded = expectations.load(path)
            self.assertEqual(len(loaded), len(table))
            row = table.iloc[0]
            self.assertAlmostEqual(loaded[(row["view"], int(row["horizon"]))]["mean"], row["mean"], places=5)
            self.assertEqual(expectations.load(Path(tmp) / "yok.csv"), {})


if __name__ == "__main__":
    unittest.main()
