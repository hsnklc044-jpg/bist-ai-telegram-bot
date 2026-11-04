"""
M32 re-validation (04.11.2026, docs/validation/M32.md): the paper book's findings fixed.

Y1  a session locked at the lower limit is locked in hourly candles too (all of its hours), so the
    hourly follow does not fill a stop at the locked price (K-75 on the live path)
O3  a position whose last session is locked down expires at the first unlocked open, not at the
    locked close
O2  /panik does not close a position at a price from before its entry
D7  no test can write the real data/panic.lock
"""

import tempfile
import unittest
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from core.market.limits import locked_down
from core.signals import panic
from core.signals import store as S

TZ = "Europe/Istanbul"


def signal(created=date(2026, 10, 1), **kw):
    return S.Signal(1, created, "X.IS", kw.pop("status", "bekliyor"), kw.pop("entry_date", None),
                    kw.pop("entry_price", None), None, None, None, None, None, None, **kw)


def hourly_day(day: str, o, h, low, c, hours=8):
    idx = pd.date_range(f"{day} 10:00", periods=hours, freq="h", tz=TZ)
    return pd.DataFrame({"open": o, "high": h, "low": low, "close": c, "volume": 1e5}, index=idx)


class HourlyLockTest(unittest.TestCase):
    def frame(self):
        return pd.concat([
            hourly_day("2026-10-01", 100, 100.5, 99.8, 100),   # signal day
            hourly_day("2026-10-02", 100, 100.5, 99.8, 100),   # entry 100 at the first hour's open
            hourly_day("2026-10-05", 90, 90, 90, 90),          # locked at the lower limit all day
            hourly_day("2026-10-06", 85, 86, 84, 85),          # first unlocked session
        ])

    def test_every_hour_of_a_locked_session_is_locked(self):
        df = self.frame()
        mask = pd.Series(locked_down(df), index=df.index)
        self.assertTrue(mask[df.index.normalize() == pd.Timestamp("2026-10-05", tz=TZ)].all())
        self.assertFalse(mask[df.index.normalize() != pd.Timestamp("2026-10-05", tz=TZ)].any())

    def test_hourly_follow_exits_at_the_first_unlocked_open(self):
        got = S._follow(signal(), self.frame(), expire=False)
        self.assertEqual(got["status"], "stop")
        self.assertEqual(got["exit_date"], "2026-10-06")
        self.assertAlmostEqual(got["exit_price"], 85.0)

    def test_an_unfinished_locked_session_does_not_fill_either(self):
        df = self.frame()
        df = df[df.index < pd.Timestamp("2026-10-05 13:00", tz=TZ)]  # 10:00-12:00 of the locked day so far
        got = S._follow(signal(), df, expire=False)
        self.assertEqual(got["status"], "acik")

    def test_daily_frames_are_unchanged(self):
        idx = pd.bdate_range("2026-10-01", periods=4)
        df = pd.DataFrame({"open": [100, 100, 90, 85], "high": [101, 101, 90, 86], "low": [99, 99, 90, 84],
                           "close": [100, 100, 90, 85]}, index=idx, dtype=float)
        self.assertEqual(locked_down(df).tolist(), [False, False, True, False])


class LockedExpiryTest(unittest.TestCase):
    def frame(self, with_next=True):
        days = pd.bdate_range("2026-10-01", periods=13)
        rows = [[100, 100.5, 99.8, 100.5]] * 10 + [[90, 90, 90, 90]]  # signal day, 9 sessions, the 10th locked
        rows[0] = [100, 100.5, 99.8, 100]
        if with_next:
            rows.append([85, 86, 84, 85])
        return pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=days[: len(rows)], dtype=float)

    def test_expiry_on_a_locked_last_session_waits_for_the_next_open(self):
        got = S._follow(signal(created=date(2026, 10, 1)), self.frame())
        self.assertEqual(got["status"], "sure")
        self.assertEqual(got["exit_price"], 85.0)
        self.assertEqual(got["exit_date"], self.frame().index[-1].date().isoformat())

    def test_without_the_next_session_it_stays_open(self):
        got = S._follow(signal(created=date(2026, 10, 1)), self.frame(with_next=False))
        self.assertEqual(got["status"], "acik")


class PanicPriceDateTest(unittest.TestCase):
    def test_a_position_entered_after_the_last_close_stays_open(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = Path(tmp) / "signals.db"
            conn = S.connect(book)
            sid = S.add(conn, date(2026, 11, 3), "X.IS", 10.0, qty=100)
            with conn:
                conn.execute("UPDATE signals SET status='acik', entry_date='2026-11-04', entry_price=10.4 WHERE id=?",
                             (sid,))
            conn.close()
            idx = pd.bdate_range("2026-10-01", "2026-11-03")
            bars = pd.DataFrame({"open": 10.0, "high": 10.1, "low": 9.9, "close": 10.0}, index=idx)
            panic.trigger(date(2026, 11, 4), lock=Path(tmp) / "panic.lock", book=book, bars=lambda s: bars)
            conn = S.connect(book)
            (s,) = S.signals(conn)
            conn.close()
        self.assertEqual(s.status, "acik")
        self.assertIsNone(s.r)

    def test_a_price_from_after_the_entry_closes_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = Path(tmp) / "signals.db"
            conn = S.connect(book)
            sid = S.add(conn, date(2026, 11, 2), "X.IS", 10.0, qty=100)
            with conn:
                conn.execute("UPDATE signals SET status='acik', entry_date='2026-11-03', entry_price=10.0 WHERE id=?",
                             (sid,))
            conn.close()
            idx = pd.bdate_range("2026-10-01", "2026-11-04")
            bars = pd.DataFrame({"open": 10.0, "high": 10.1, "low": 9.9, "close": np.r_[[10.0] * (len(idx) - 1), 9.5]},
                                index=idx)
            panic.trigger(date(2026, 11, 4), lock=Path(tmp) / "panic.lock", book=book, bars=lambda s: bars)
            conn = S.connect(book)
            (s,) = S.signals(conn)
            conn.close()
        self.assertEqual(s.status, "panik")
        self.assertAlmostEqual(s.exit_price, 9.5)


class VerdictWordTest(unittest.TestCase):
    def test_short_restricted_verdict_is_read(self):
        from core.reports import validation as V

        self.assertEqual(V._verdict("Karar: kısıtlı — gerekçe"), "kısıtlı kullanılabilir")
        self.assertEqual(V._verdict("**Karar: kullanılamaz.** gerekçe"), "kullanılamaz")
        self.assertEqual(V.reports()["M32"].verdict, "kısıtlı kullanılabilir")
        self.assertEqual(V.reports()["M31"].verdict, "kullanılamaz")


class PanicIsolationTest(unittest.TestCase):
    def test_tests_never_see_the_real_panic_lock(self):
        from core.config.paths import DATA_DIR

        self.assertNotEqual(Path(panic.PANIC_FILE).resolve().parent, Path(DATA_DIR).resolve())


if __name__ == "__main__":
    unittest.main()
