"""
Özellik B §4.1: the templates' card counts every decided scenario of the screening period with
the same outcome rule as the live record; nothing after SCREEN_END is read.
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

from core.analytics import scenarios as S
from core.analytics import scenarios_study as St
from tests.test_scenarios import walk


class SummaryTest(unittest.TestCase):
    def test_by_hand(self):
        events = [("A", pd.Timestamp("2025-01-02"), "hedef", 2.0, 0.05),
                  ("A", pd.Timestamp("2025-01-03"), "geçersizlik", -1.0, -0.03),
                  ("B", pd.Timestamp("2025-01-06"), "geçersizlik", -1.0, -0.02),
                  ("B", pd.Timestamp("2025-01-07"), "süre doldu", 0.5, 0.01),
                  ("C", pd.Timestamp("2025-01-08"), "dolmadı", None, None)]
        card = St.summarize(events)
        self.assertEqual((card.events, card.stocks, card.unfilled), (4, 2, 1))
        self.assertAlmostEqual(card.target, 0.25)
        self.assertAlmostEqual(card.invalidation, 0.5)
        self.assertAlmostEqual(card.mean_r, 0.125)
        self.assertAlmostEqual(card.excess, 0.0025)
        self.assertEqual(card.worst_streak, 2)
        self.assertIn("4 olay (2 hisse)", card.line())

    def test_empty(self):
        self.assertEqual(St.summarize([]).line(), "olay yok")


class StudyTest(unittest.TestCase):
    def test_same_rule_as_live_and_no_holdout(self):
        from core.backtest import run

        df = walk(n=700)
        bench = walk(n=700, seed=9)
        end = df.index[600]
        with mock.patch.object(run, "SCREEN_END", end), mock.patch("core.screen.card.HISTORY_START", "2024-06-03"):
            cards = St.study(({"A.IS": df}, bench, None))
            changed = df.copy()
            changed.loc[end + pd.Timedelta(days=1):, ["open", "high", "low", "close"]] *= 3  # the holdout moves
            again = St.study(({"A.IS": changed}, bench, None))
        self.assertEqual({k: v.line() for k, v in cards.items()}, {k: v.line() for k, v in again.items()})
        total = sum(c.events for c in cards.values())
        self.assertGreater(total, 0)

        events = St.stock_events(df.loc[:end], bench.loc[:end], None)
        for name, rows in events.items():
            table = S.signals(df.loc[:end])[name]
            for day, result, r, _ in rows:
                t = df.index.get_loc(day)
                o = S.outcome(df.loc[:end], t, table["invalidation"].iloc[t], table["target"].iloc[t])
                self.assertEqual(o.result, result)
                if r is not None:
                    self.assertAlmostEqual(o.r, r)

    def test_cache_for_the_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cards.json"
            St.save({name: St.Card(events=3, stocks=1, target=1.0, invalidation=0.0, timeout=0.0, mean_r=1.2)
                     for name in S.TEMPLATES}, path)
            lines = St.load_lines(path)
        self.assertEqual(set(lines), set(S.TEMPLATES))
        self.assertTrue(all("3 olay" in v for v in lines.values()))
        self.assertEqual(St.load_lines(Path("/yok/cards.json")), {})
        self.assertTrue(np.isnan(St.Card().mean_r))


if __name__ == "__main__":
    unittest.main()
