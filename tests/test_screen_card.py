"""
/tara Aşama 3: an honest history card. Next session's open as entry (no look-ahead), costs,
mean and median, hit rate, samples and independent events (overlapping signals of one stock
counted once), a block-bootstrap 95% interval, the result without the 5 best stocks, labels
that never call a past result evidence, the number of criteria tried, a cache keyed by the
data version, and the holdout line enforced through load_frames.
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

from core.screen import card
from core.screen.language import parse


def flat(n=300, start="2024-01-02", price=100.0):
    index = pd.bdate_range(start, periods=n)
    return pd.DataFrame({"open": price, "high": price, "low": price, "close": price, "volume": 1e6},
                        index=index, dtype=float)


class EntryAndCostTest(unittest.TestCase):
    def test_next_open_entry_cost_and_xu100(self):
        stock, bench = flat(), flat()
        day = stock.index[100]
        stock["kapanis_mark"] = 0.0
        # the condition holds on `day` only; entry at the NEXT open, exit at the close 5 sessions after
        stock.loc[day, "close"] = 101.0  # makes kapanis>100.5 true on that day alone
        stock.loc[stock.index[101], "open"] = 100.0
        stock.loc[stock.index[105], "close"] = 110.0
        bench.loc[bench.index[105], "close"] = 102.0
        stats = card.history(parse("kapanis 100,5..105"), {"A.IS": stock.drop(columns="kapanis_mark")}, bench,
                             horizons=(5,))[5]
        self.assertEqual((stats.n, stats.independent), (1, 1))
        expected = (110 / 100 - 1) - card.ROUND_TRIP_COST - (102 / 100 - 1)
        self.assertAlmostEqual(stats.mean, expected)
        self.assertAlmostEqual(card.ROUND_TRIP_COST, 2 * (0.0010 + 0.0005))

    def test_a_signal_on_the_last_screening_day_has_no_exit(self):
        stock, bench = flat(), flat()
        stock.loc[stock.index[-1], "close"] = 101.0
        self.assertEqual(card.history(parse("kapanis>100,5"), {"A.IS": stock}, bench, horizons=(5,))[5].n, 0)


class OverlapTest(unittest.TestCase):
    def test_overlapping_signals_of_one_stock_count_once(self):
        stock, bench = flat(), flat()
        days = stock.index[100:110]  # ten days in a row
        stock.loc[days, "close"] = 101.0
        stats = card.history(parse("kapanis>100,5"), {"A.IS": stock}, bench, horizons=(5,))[5]
        self.assertEqual(stats.n, 10)
        self.assertEqual(stats.independent, 2)  # day 0 and day 5: no two share a holding period


def noisy_market(drift_good=0.0, n_stocks=12, seed=0):
    rng = np.random.default_rng(seed)
    index = pd.bdate_range("2023-06-01", "2026-10-30")
    frames = {}
    for i in range(n_stocks):
        r = rng.normal(drift_good if i < 6 else 0.0, 0.01, len(index))
        c = 100 * np.exp(np.cumsum(r))
        frames[f"S{i:02d}.IS"] = pd.DataFrame({"open": c, "high": c * 1.01, "low": c * 0.99, "close": c,
                                               "volume": 1e6}, index=index)
    b = 100 * np.exp(np.cumsum(rng.normal(0, 0.008, len(index))))
    return frames, pd.DataFrame({"open": b, "high": b, "low": b, "close": b, "volume": 1e6}, index=index)


class StatisticsTest(unittest.TestCase):
    def test_interval_median_and_without_the_best_five(self):
        frames, bench = noisy_market()
        stats = card.history(parse("kapanis>0"), frames, bench, horizons=(20,))[20]
        self.assertGreater(stats.n, 1000)
        self.assertLess(stats.low, stats.mean)
        self.assertGreater(stats.high, stats.mean)
        self.assertIsNotNone(stats.median)
        self.assertIsNotNone(stats.without_top)
        self.assertEqual(stats.label, "geçmişte XU100'den ayırt edilemiyor")
        again = card.history(parse("kapanis>0"), frames, bench, horizons=(20,))[20]
        self.assertEqual((again.low, again.high), (stats.low, stats.high))  # fixed seed

    def test_labels(self):
        self.assertEqual(card.CardStats(n=12).label, "yetersiz örnek")
        positive = card.CardStats(n=500, independent=100, mean=0.02, median=0.01, hit=0.6, low=0.005, high=0.03,
                                  without_top=0.01)
        self.assertEqual(positive.label,
                         "geçmişte olumlu; çoklu deneme nedeniyle şans olabilir, kanıt değildir")
        negative = card.CardStats(n=500, independent=100, mean=-0.02, median=-0.01, hit=0.4, low=-0.03,
                                  high=-0.005, without_top=-0.02)
        self.assertEqual(negative.label, "geçmişte XU100'ün gerisinde; kanıt değildir")

    def test_lines(self):
        from core.screen import command

        stats = {5: card.CardStats(n=500, independent=90, mean=0.004, median=0.002, hit=0.53, low=-0.002,
                                   high=0.01, without_top=0.001),
                 20: card.CardStats(n=12)}
        text = "\n".join(command.card_lines(stats, trials=(3, 7)))
        for part in ("ortalama +%0,4", "medyan +%0,2", "isabet %53", "örnek 500", "bağımsız 90",
                     "%95 aralık [-%0,2, +%1,0]", "en kârlı 5 hisse hariç +%0,1", "ayırt edilemiyor",
                     "20 seans: yetersiz örnek (12)", "bu oturumda 3. deneme", "bugüne kadar 7 farklı kriter",
                     "maliyet dahil"):
            self.assertIn(part, text)


class TrialTest(unittest.TestCase):
    def test_distinct_criteria_per_session_and_in_total(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "screen_trials.csv"
            session: dict = {}
            self.assertEqual(card.record_trial(1, "rsi<30", path=path, session=session), (1, 1))
            self.assertEqual(card.record_trial(1, "rsi<30", path=path, session=session), (1, 1))  # same one
            self.assertEqual(card.record_trial(1, "rsi<35", path=path, session=session), (2, 2))
            self.assertEqual(card.record_trial(1, "rsi<40", path=path, session={}), (1, 3))  # a new session


class CacheTest(unittest.TestCase):
    def test_same_criterion_and_data_is_computed_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp) / "cards.json"
            frames, bench = noisy_market(n_stocks=3)
            data = (frames, bench, None)
            with mock.patch.object(card, "history", wraps=card.history) as computed:
                first = card.cached_history(parse("kapanis>0"), lambda: data, version="v1", path=store)
                second = card.cached_history(parse("kapanis>0"), lambda: data, version="v1", path=store)
                self.assertEqual(computed.call_count, 1)
                self.assertEqual(first, second)
                card._MEMORY.clear()  # a restart: read back from disk
                self.assertEqual(card.cached_history(parse("kapanis>0"), lambda: data, version="v1", path=store),
                                 first)
                self.assertEqual(computed.call_count, 1)
                card.cached_history(parse("kapanis>0"), lambda: data, version="v2", path=store)  # data changed
                self.assertEqual(computed.call_count, 2)
            card._MEMORY.clear()

    def test_data_version_follows_the_corrections(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp) / "corporate_actions.csv"
            a.write_text("symbol,ex_date\n", encoding="utf-8")
            before = card.data_version([a])
            a.write_text("symbol,ex_date\nX.IS,2026-10-19\n", encoding="utf-8")
            self.assertNotEqual(card.data_version([a]), before)


class HoldoutTest(unittest.TestCase):
    def test_history_data_goes_through_load_frames_without_the_holdout(self):
        from core.screen import command

        command._HISTORY.clear()
        index = pd.bdate_range("2026-10-01", periods=5)
        frame = pd.DataFrame({"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1.0}, index=index)
        with mock.patch("core.backtest.run.load_frames", return_value={"A.IS": frame, "XU100.IS": frame}) as load, \
                mock.patch("core.market.membership.ever_members", return_value=["A.IS"]), \
                mock.patch("core.market.membership.membership_panel", return_value=None):
            command._history_data()
        for call in load.call_args_list:
            self.assertFalse(call.kwargs.get("include_holdout", False))
        command._HISTORY.clear()


if __name__ == "__main__":
    unittest.main()
