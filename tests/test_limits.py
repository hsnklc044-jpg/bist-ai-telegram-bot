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
