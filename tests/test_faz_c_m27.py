"""
Faz C, M27 (the scenario templates' card, docs/validation/M27.md). Not K-64.

M27-4  the interval is of the same mean the card shows (events weighted, whole days resampled)
M27-8  a signal whose full horizon is not inside the period is not counted (only the early
       finishers of the last 20 sessions used to enter the card)
"""

import unittest

import numpy as np
import pandas as pd

from core.analytics import scenarios as S
from core.analytics import scenarios_study as St
from tests.test_scenarios import walk


def crowded_events():
    """Quiet days with one good event; a few crowded days with many bad ones."""

    rng = np.random.default_rng(0)
    days = pd.bdate_range("2024-01-02", periods=200)
    events = []
    for i, d in enumerate(days):
        if i % 20 == 0:  # a crowded day: 30 losing events
            events += [("S", d, "geçersizlik", -1.0, -0.02)] * 30
        else:
            events.append(("S", d, "hedef", float(rng.uniform(0.9, 1.0)), 0.01))
    return events


class IntervalWeightTest(unittest.TestCase):
    def test_interval_covers_the_shown_mean(self):
        card = St.summarize(crowded_events())
        self.assertLess(card.mean_r, 0)  # events weighted: the crowded days dominate
        self.assertLessEqual(card.low, card.mean_r)
        self.assertGreaterEqual(card.high, card.mean_r)


class PeriodEndTest(unittest.TestCase):
    def test_last_signals_without_their_full_horizon_are_left_out(self):
        from unittest import mock

        df, bench = walk(n=400), walk(n=400, seed=9)
        every_day = {name: pd.DataFrame({"ok": True, "invalidation": 1.0, "target": 1e9}, index=df.index)
                     for name in S.TEMPLATES}

        def early(frame, t, invalidation, target):  # every signal finishes the next day
            return S.Outcome("hedef", 100.0, 101.0, 1, 0.5, frame.index[min(t + 1, len(frame) - 1)])

        with mock.patch.object(S, "signals", return_value=every_day), mock.patch.object(S, "outcome", side_effect=early):
            events = St.stock_events(df, bench, None)
        self.assertTrue(any(rows for rows in events.values()))
        for rows in events.values():
            for day, *_ in rows:
                self.assertLess(df.index.get_loc(day) + S.HORIZON, len(df))

    def test_earlier_signals_are_kept(self):
        df, bench = walk(n=400), walk(n=400, seed=9)
        self.assertGreater(sum(len(v) for v in St.stock_events(df, bench, None).values()), 0)


if __name__ == "__main__":
    unittest.main()
