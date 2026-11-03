"""
BIST 30 hedefi, adım 3 (K-60): the paper signal book in SQLite. Each case is computed by hand:
entry at the next open, 2% stop, 4% target, at most 10 sessions, the same rules as the ML labels;
the book's value at each close; the 6% breaker refuses the signals of the session that fell.
"""

import tempfile
import unittest
from datetime import date
from pathlib import Path

import pandas as pd

from core.ml.features import COST
from core.signals import store as S


def bars(rows, first="2026-11-02"):
    index = pd.bdate_range(first, periods=len(rows))
    o, h, low, c = zip(*rows, strict=True)
    return pd.DataFrame({"open": o, "high": h, "low": low, "close": c, "volume": 1e6}, index=index)


class BookTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.conn = S.connect(Path(tmp.name) / "signals.db")
        self.addCleanup(self.conn.close)

    def test_waits_then_reaches_the_target(self):
        df = bars([(100, 100, 100, 100), (100, 101, 99, 100), (101, 104.5, 100, 104)])
        self.assertIsNotNone(S.add(self.conn, date(2026, 11, 2), "A.IS", 100.0, 0.7))
        self.assertIsNone(S.add(self.conn, date(2026, 11, 2), "A.IS", 100.0, 0.7))  # once per stock and day
        S.update(self.conn, lambda s: df.iloc[:1])
        self.assertEqual(S.signals(self.conn)[0].status, "bekliyor")  # no next session yet
        S.update(self.conn, lambda s: df.iloc[:2])
        s = S.signals(self.conn)[0]
        self.assertEqual((s.status, s.entry_price, s.stop, s.target), ("acik", 100.0, 98.0, 104.0))
        S.update(self.conn, lambda s: df)
        s = S.signals(self.conn)[0]
        self.assertEqual((s.status, s.exit_date), ("hedef", date(2026, 11, 4)))
        self.assertAlmostEqual(s.r, 0.04 - COST)

    def test_stop_gap_and_expiry(self):
        gap = bars([(100, 100, 100, 100), (100, 100, 99, 100), (95, 96, 94, 95)])
        S.add(self.conn, date(2026, 11, 2), "G.IS", 100.0)
        flat = bars([(50, 50, 50, 50)] + [(50, 50.5, 49.5, 50.2)] * 10)
        S.add(self.conn, date(2026, 11, 2), "F.IS", 50.0)
        S.update(self.conn, lambda s: gap if s == "G.IS" else flat)
        by = {s.symbol: s for s in S.signals(self.conn)}
        self.assertEqual(by["G.IS"].status, "stop")
        self.assertAlmostEqual(by["G.IS"].r, 0.95 - 1 - COST)  # filled at the open below the stop
        self.assertEqual(by["F.IS"].status, "sure")
        self.assertAlmostEqual(by["F.IS"].r, 50.2 / 50 - 1 - COST)

    def test_limit_up_open_is_not_filled(self):
        S.add(self.conn, date(2026, 11, 2), "L.IS", 100.0)
        S.update(self.conn, lambda s: bars([(100, 100, 100, 100), (110, 110, 110, 110)]))
        self.assertEqual(S.signals(self.conn)[0].status, "dolmadi")

    def test_equity_and_breaker(self):
        # two signals of 10.000 TL each; on 05.11 both lose 30%: the book falls 6.000 TL = -6%
        rows = [(100, 100, 100, 100), (100, 100, 100, 100), (100, 100, 99, 100), (70, 70, 70, 70)]
        df = bars(rows)
        S.add(self.conn, date(2026, 11, 2), "A.IS", 100.0)
        S.add(self.conn, date(2026, 11, 2), "B.IS", 100.0)
        S.update(self.conn, lambda s: df.iloc[:3])  # entered at 100, both open
        values = S.equity(self.conn, lambda s: df, [date(2026, 11, 4), date(2026, 11, 5)])
        self.assertEqual(values.iloc[0], S.CAPITAL)
        change = S.check_breaker(self.conn, lambda s: df.iloc[:4], date(2026, 11, 5), date(2026, 11, 4))
        self.assertAlmostEqual(change, -0.06)
        with self.assertRaises(S.BreakerTripped):
            S.add(self.conn, date(2026, 11, 5), "C.IS", 100.0)
        self.assertIsNotNone(S.add(self.conn, date(2026, 11, 6), "C.IS", 100.0))  # the next close is free
        text = S.summary(self.conn, lambda s: df, date(2026, 11, 5))
        self.assertIn("Şalter açık", text)

    def test_small_fall_does_not_trip(self):
        df = bars([(100, 100, 100, 100), (100, 100, 100, 100), (99, 99, 99, 99)])
        S.add(self.conn, date(2026, 11, 2), "A.IS", 100.0)
        S.update(self.conn, lambda s: df.iloc[:2])
        self.assertAlmostEqual(S.check_breaker(self.conn, lambda s: df, date(2026, 11, 4), date(2026, 11, 3)),
                               -0.001)
        self.assertFalse(S.blocked(self.conn, date(2026, 11, 4)))

    def test_personal_file(self):
        from core import backup
        from core.config.paths import ROOT_DIR, SIGNALS_DB

        self.assertIn(SIGNALS_DB, backup.PERSONAL_FILES)
        self.assertIn("data/*.db", (ROOT_DIR / ".gitignore").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
