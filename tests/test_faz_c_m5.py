"""
Faz C, M5 (the /tara history card): the card's method fixed (docs/validation/M5.md). Not K-64.

M5-2  the universe check (candles, unresolved jumps) reads only data before the holdout
M5-5  a stock whose data ends (delisted) keeps its last events: exit at its last close
M5-7  the bootstrap block is at least twice the holding period
M5-8  the card also counts independent entry dates (stocks of one day move together)
M5-9  membership is not carried past the end of the membership table
"""

import unittest
from unittest import mock

import numpy as np
import pandas as pd

from core.screen import card
from core.screen.language import parse
from tests.test_screen_card import flat, noisy_market


class DelistedTest(unittest.TestCase):
    def test_last_events_of_a_stock_whose_data_ends_count(self):
        bench = flat(300)
        stock = flat(300).iloc[:200].copy()  # data ends at row 199 (delisted), the index goes on
        day = stock.index[195]
        stock.loc[day, "close"] = 101.0       # kapanis>100,5 only on row 195
        stock.loc[stock.index[196], "open"] = 100.0
        stock.loc[stock.index[199], "close"] = 60.0  # the last close: −40%
        stats = card.history(parse("kapanis>100,5"), {"A.IS": stock}, bench, horizons=(20,))[20]
        self.assertEqual(stats.n, 1)
        self.assertAlmostEqual(stats.mean, (60 / 100 - 1) - 0 - card.ROUND_TRIP_COST)

    def test_events_at_the_end_of_the_period_still_wait(self):
        bench, stock = flat(300), flat(300)
        stock.loc[stock.index[290], "close"] = 101.0  # 20 sessions are not there yet for anyone
        stats = card.history(parse("kapanis>100,5"), {"A.IS": stock}, bench, horizons=(20,))[20]
        self.assertEqual(stats.n, 0)


class BlockTest(unittest.TestCase):
    def test_block_is_at_least_twice_the_horizon(self):
        self.assertEqual(card.block_for(5), card.BLOCK)
        self.assertEqual(card.block_for(20), 40)

    def test_interval_uses_the_longer_block(self):
        days = np.random.default_rng(0).normal(0, 0.01, 500)
        with mock.patch.object(card, "_interval", wraps=card._interval) as spy:
            frames, bench = noisy_market()
            card.history(parse("kapanis>0"), frames, bench, horizons=(20,))
        self.assertEqual(spy.call_args.kwargs.get("block"), 40)
        self.assertEqual(len(card._interval(days, block=40)), 2)


class IndependentDatesTest(unittest.TestCase):
    def test_same_day_signals_of_many_stocks_are_one_date(self):
        frames, bench = noisy_market()
        stats = card.history(parse("kapanis>0"), frames, bench, horizons=(20,))[20]
        self.assertGreater(stats.independent_dates, 0)
        self.assertLess(stats.independent_dates, stats.independent)  # 12 stocks, the same dates
        sessions = len(bench.loc[card.HISTORY_START:card_end()])
        self.assertLessEqual(stats.independent_dates, sessions // 20 + 1)


def card_end():
    from core.backtest.run import SCREEN_END

    return SCREEN_END


class MembershipEndTest(unittest.TestCase):
    def test_membership_is_not_carried_past_the_table(self):
        bench, stock = flat(300, start="2023-08-01"), flat(300, start="2023-08-01")
        stock.loc[stock.index[250], "close"] = 101.0  # after the table ends (row 129)
        eligible = pd.DataFrame({"A.IS": True}, index=stock.index[:130])
        stats = card.history(parse("kapanis>100,5"), {"A.IS": stock}, bench, eligible=eligible, horizons=(5,))[5]
        self.assertEqual(stats.n, 0)


class UniverseCheckTest(unittest.TestCase):
    def test_tradable_symbols_can_stop_before_the_holdout(self):
        from core.backtest import run

        seen = {}

        def build(symbols, before=None):
            seen["before"] = before
            return []

        with mock.patch.object(run, "build_report", side_effect=build):
            run.tradable_symbols(["A.IS"], before=pd.Timestamp("2026-11-02"))
        self.assertEqual(seen["before"], pd.Timestamp("2026-11-02"))

    def test_quality_report_cuts_before(self):
        from core.market import quality

        idx = pd.bdate_range("2026-09-01", "2026-11-20")
        df = pd.DataFrame({"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 1e6}, index=idx)
        with mock.patch.object(quality.store, "read", return_value=df), \
                mock.patch.object(quality, "clean", side_effect=lambda d, s: d), \
                mock.patch.object(quality, "drop_open_candle", side_effect=lambda d: d), \
                mock.patch.object(quality, "check_symbol", side_effect=lambda f, s, c, m: (s, f.index.max())):
            got = dict(quality.build_report(["A.IS"], before=pd.Timestamp("2026-11-02")))
        self.assertLess(got["A.IS"], pd.Timestamp("2026-11-02"))

    def test_the_card_universe_uses_the_cut(self):
        import inspect

        from core.screen import command

        self.assertTrue("before=HOLDOUT_START" in inspect.getsource(command), "the card's universe check is not cut")


if __name__ == "__main__":
    unittest.main()
