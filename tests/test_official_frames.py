"""Price frames for research from the official data (r1, K-91). Written before the code and before any measurement.

A corporate action day (the exchange's code 01, 03, 04, 05, 99; not 06 cash dividend) takes XU100's return instead
of the stock's raw jump; the series before it is scaled so the returns are continuous; share counts are scaled the
other way, so the lira volume stays as traded. The benchmark is the official XU100. Membership is the official
daily flag. Nothing after the end date is ever loaded."""

import unittest
from datetime import date

import pandas as pd
import pytest

from core.official import frames as OF
from core.official import indices, prices


@pytest.fixture(autouse=True)
def _db(tmp_path, monkeypatch):
    monkeypatch.setattr(prices, "OFFICIAL_DB", tmp_path / "official.db")


DAYS = pd.bdate_range("2016-01-04", periods=6)


def put(code, closes, actions=None, members=None, quantity=1000.0):
    actions = actions or {}
    members = members or {}
    with prices._connect() as conn:
        for i, (d, c) in enumerate(zip(DAYS, closes)):
            conn.execute("INSERT INTO official_prices (code, date, open, high, low, close, prev_close, value, quantity, "
                         "bist100, bist30, corp_action, file) VALUES (?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, 0, ?, 'f')",
                         (code, d.date().isoformat(), c, c * 1.01, c * 0.99, c, c * quantity, quantity,
                          members.get(i, 1), actions.get(i)))


def put_index(values):
    with prices._connect() as conn:
        indices._schema(conn)
        conn.executemany("INSERT INTO official_indices VALUES ('XU100', ?, ?, ?, ?, NULL, 1, 'f')",
                         [(d.date().isoformat(), v, v, v) for d, v in zip(DAYS, values)])


class FramesTest(unittest.TestCase):
    def test_a_bonus_day_takes_the_index_return_and_the_past_is_scaled(self):
        put("AAA", [100, 102, 51, 52, 53, 54], actions={2: "03"})  # a 1:1 bonus on day 2
        put_index([1000, 1010, 1020, 1030, 1040, 1050])
        frames, bench, eligible = OF.load(date(2016, 1, 4), date(2016, 1, 11))
        close = frames["AAA.IS"]["close"]
        r = close.pct_change()
        self.assertAlmostEqual(r.iloc[2], 1020 / 1010 - 1)  # XU100's return, not -50 %
        self.assertAlmostEqual(r.iloc[3], 52 / 51 - 1)  # raw returns elsewhere
        self.assertAlmostEqual(close.iloc[-1], 54)  # the latest prices are the traded ones
        tl = frames["AAA.IS"]["close"] * frames["AAA.IS"]["volume"]
        self.assertAlmostEqual(tl.iloc[0], 100 * 1000)  # lira volume as traded
        self.assertEqual(list(bench["close"]), [1000, 1010, 1020, 1030, 1040, 1050])

    def test_a_cash_dividend_day_stays_raw(self):
        put("BBB", [100, 100, 95, 95, 95, 95], actions={2: "06"})
        put_index([1000] * 6)
        frames, _, _ = OF.load(date(2016, 1, 4), date(2016, 1, 11))
        self.assertAlmostEqual(frames["BBB.IS"]["close"].pct_change().iloc[2], -0.05)

    def test_membership_from_the_daily_flag_and_nothing_after_the_end(self):
        put("CCC", [10] * 6, members={0: 1, 1: 1, 2: 0, 3: 0, 4: 1, 5: 1})
        put_index([1000] * 6)
        frames, bench, eligible = OF.load(date(2016, 1, 4), date(2016, 1, 8))
        self.assertEqual(list(eligible["CCC.IS"]), [True, True, False, False, True])
        self.assertEqual(frames["CCC.IS"].index[-1], pd.Timestamp("2016-01-08"))
        self.assertEqual(bench.index[-1], pd.Timestamp("2016-01-08"))

    def test_a_combined_code_with_a_split_part_is_filled(self):
        self.assertTrue(OF.is_adjusting("01&03"))
        self.assertTrue(OF.is_adjusting("03-06"))
        self.assertFalse(OF.is_adjusting("06"))
        self.assertFalse(OF.is_adjusting(None))


class GuardTest(unittest.TestCase):
    def test_the_end_can_never_reach_the_holdout(self):
        from core.backtest.run import HOLDOUT_START

        with self.assertRaises(ValueError):
            OF.load(date(2016, 1, 4), HOLDOUT_START)


if __name__ == "__main__":
    unittest.main()
