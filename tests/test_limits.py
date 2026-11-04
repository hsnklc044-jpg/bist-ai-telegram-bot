"""
Faz B, step 1 (K-75): one limit rule for every module. BIST's daily limit is ±10%; a move of 9.5% or
more counts as a limit move. The modules compared it in eleven places, some with > and some with >=,
none with a tolerance, so 100 → 109,5 was a limit in one module and not in another.
"""

import re
import unittest
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from core.market import limits


class RuleTest(unittest.TestCase):
    def test_the_line_itself_is_a_limit(self):
        self.assertTrue(limits.limit_up(109.5 / 100 - 1))  # 0.09499999... in floating point
        self.assertTrue(limits.limit_down(90.5 / 100 - 1))
        self.assertTrue(limits.limit_move(-0.0950000001))
        self.assertFalse(limits.limit_up(0.0949))
        self.assertTrue(np.array_equal(limits.limit_up(np.array([0.0949, 109.5 / 100 - 1])), [False, True]))

    def test_no_module_compares_on_its_own(self):
        root = Path(limits.__file__).resolve().parents[1]
        own = []
        for path in root.rglob("*.py"):
            if path.name == "limits.py":
                continue
            for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if re.search(r"[<>]=?\s*-?\s*(cfg\.)?LIMIT_MOVE\b", line):
                    own.append(f"{path.relative_to(root)}:{n}")
        self.assertEqual(own, [])


class ModulesAgreeTest(unittest.TestCase):
    """100 → 109,5 at the open is a limit-up open everywhere: no entry."""

    def frame(self):
        idx = pd.bdate_range("2026-01-01", periods=15)
        df = pd.DataFrame({"open": 100.0, "high": 100.5, "low": 99.5, "close": 100.0, "volume": 1e6}, index=idx)
        df.iloc[1, :4] = 109.5
        return df

    def test_book_labels_and_scenarios(self):
        from core.analytics import scenarios
        from core.ml import features
        from core.signals import store

        df = self.frame()
        s = store.Signal(1, date(2026, 1, 1), "A.IS", "bekliyor", None, None, None, None, None, None, None, None)
        self.assertEqual(store._follow(s, df)["status"], "dolmadi")
        self.assertTrue(np.isnan(features.labels(df, horizon=10)["label"].iloc[0]))
        self.assertEqual(scenarios.outcome(df, 0, 95.0, 120.0).result, "dolmadı")


class LockedDaysTest(unittest.TestCase):
    """K-75 decision 2: no exit on a day locked at the lower limit, no entry on one locked at the upper
    limit (M32-9, M27-6, M30-5, M5-3). The exit is the first unlocked open."""

    def frame(self):
        idx = pd.bdate_range("2026-01-01", periods=14)
        df = pd.DataFrame({"open": 100.0, "high": 100.5, "low": 99.5, "close": 100.0, "volume": 1e6}, index=idx)
        df.iloc[2, :4] = 89.0  # locked at the lower limit: open = high = low = close = 89 (−11%)
        df.iloc[3, :4] = [88.0, 90.0, 87.0, 89.5]  # the first unlocked day opens at 88
        return df

    def test_the_mask(self):
        df = self.frame()
        self.assertEqual(list(np.flatnonzero(limits.locked_down(df))), [2])

    def test_book_exits_at_the_first_unlocked_open(self):
        from core.signals import store

        s = store.Signal(1, date(2026, 1, 1), "A.IS", "bekliyor", None, None, None, None, None, None, None, None)
        got = store._follow(s, self.frame())
        self.assertEqual((got["status"], got["exit_price"], got["exit_date"]), ("stop", 88.0, "2026-01-06"))

    def test_ml_labels_exit_at_the_first_unlocked_open(self):
        from core.ml import features

        got = features.labels(self.frame(), horizon=10)
        self.assertEqual(got["label"].iloc[0], 0.0)
        self.assertAlmostEqual(got["r"].iloc[0], 88 / 100 - 1 - features.COST)

    def test_scenarios_exit_at_the_first_unlocked_open(self):
        from core.analytics import scenarios

        o = scenarios.outcome(self.frame(), 0, 95.0, 120.0)
        self.assertEqual((o.result, o.exit), ("geçersizlik", 88.0))

    def test_card_does_not_fill_on_a_locked_up_entry(self):
        from core.screen import card
        from core.screen.language import parse
        from tests.test_screen_card import flat

        stock, bench = flat(), flat()
        stock.loc[stock.index[100], "close"] = 101.0  # the condition holds on that day
        stock.iloc[101, :4] = 111.1  # the entry day is locked at the upper limit
        stock.iloc[102:, :4] = 111.1
        stats = card.history(parse("kapanis 100,5..105"), {"A.IS": stock}, bench, horizons=(5,))[5]
        self.assertEqual(stats.n, 0)
