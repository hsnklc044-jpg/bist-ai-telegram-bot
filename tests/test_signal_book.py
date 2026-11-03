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
        # K-67: the entry day's high 101 lifts the trailing stop to 101 × 0,98 = 98,98
        self.assertEqual((s.status, s.entry_price, s.target, s.peak), ("acik", 100.0, 104.0, 101.0))
        self.assertAlmostEqual(s.stop, 98.98)
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

    def test_equity(self):
        df = bars([(100, 100, 100, 100), (100, 100, 100, 100), (100, 100, 99, 100), (70, 70, 70, 70)])
        S.add(self.conn, date(2026, 11, 2), "A.IS", 100.0)
        S.update(self.conn, lambda s: df.iloc[:3])  # entered at 100, open
        values = S.equity(self.conn, lambda s: df, [date(2026, 11, 4)])
        self.assertEqual(values.iloc[0], S.CAPITAL)

    def test_breaker_on_the_days_closed_losses(self):
        # K-65: two signals of 10.000 TL each gap down to 70 on 05.11 and stop at that open:
        # 2 × 10.000 × (−30% − cost) = −6.030 TL = −6,03% of 100.000 → the bot locks itself that day
        df = bars([(100, 100, 100, 100), (100, 100, 100, 100), (100, 100, 99, 100), (70, 70, 70, 70)])
        S.add(self.conn, date(2026, 11, 2), "A.IS", 100.0)
        S.add(self.conn, date(2026, 11, 2), "B.IS", 100.0)
        S.update(self.conn, lambda s: df)
        self.assertEqual({s.status for s in S.signals(self.conn)}, {"stop"})
        self.assertAlmostEqual(S.realized(self.conn, date(2026, 11, 5)), 2 * (0.70 - 1 - COST) * S.SIZE / S.CAPITAL)
        S.check_breaker(self.conn, date(2026, 11, 5))
        self.assertTrue(S.blocked(self.conn, date(2026, 11, 5)))
        with self.assertRaises(S.BreakerTripped):
            S.add(self.conn, date(2026, 11, 5), "C.IS", 100.0)
        self.assertIsNotNone(S.add(self.conn, date(2026, 11, 6), "C.IS", 100.0))  # the next day is free
        self.assertIn("Şalter açık", S.summary(self.conn, lambda s: df, date(2026, 11, 5)))

    def test_small_loss_and_open_losses_do_not_trip(self):
        # one ordinary stop: −2% − cost of 10.000 TL = −0,215% of the book; an open loss never counts
        df = bars([(100, 100, 100, 100), (100, 100, 100, 100), (99, 99, 97.9, 98)])
        S.add(self.conn, date(2026, 11, 2), "A.IS", 100.0)
        S.update(self.conn, lambda s: df)
        self.assertAlmostEqual(S.check_breaker(self.conn, date(2026, 11, 4)), (-0.02 - COST) * S.SIZE / S.CAPITAL)
        self.assertFalse(S.blocked(self.conn, date(2026, 11, 4)))

    def test_personal_file(self):
        from core import backup
        from core.config.paths import ROOT_DIR, SIGNALS_DB

        self.assertIn(SIGNALS_DB, backup.PERSONAL_FILES)
        self.assertIn("data/*.db", (ROOT_DIR / ".gitignore").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()


class ScreenOptionTest(unittest.TestCase):
    def setUp(self):
        from tests.test_screen_engine import walk

        self.frames = {"A.IS": walk(320, seed=1), "B.IS": walk(320, seed=2)}
        self.bench = walk(320, seed=3)

    def run_query(self, text, report=None, proba=None):
        from unittest import mock

        from core.screen import engine
        from core.screen.language import parse

        q = parse(text)
        with mock.patch("core.ml.ml_filter.load", return_value=report), \
                mock.patch("core.ml.live.probabilities", return_value=proba or {}):
            return q, engine.run(q, self.frames, self.bench, actions=[])

    def test_parse(self):
        from core.screen.language import ScreenError, parse

        self.assertTrue(parse("kapanis>0 ml=evet").ml)
        self.assertFalse(parse("kapanis>0").ml)
        self.assertIn("ml=evet", parse("kapanis>0 ml=evet ele=hayir").text)
        with self.assertRaises(ScreenError):
            parse("kapanis>0 ml=belki")

    def test_closed_filter_empties_the_list_and_says_why(self):
        from core.screen.command import format_result

        _, result = self.run_query("kapanis>0 ml=evet ele=hayir", {"passed": False, "reason": "isabet %52,0 < eşik %60"})
        self.assertEqual(result.matches, [])
        text = format_result(result, None)
        self.assertIn("ML filtresi kapalı (isabet %52,0 < eşik %60)", text)
        _, plain = self.run_query("kapanis>0 ele=hayir")
        self.assertEqual(len(plain.matches), 2)  # without ml= nothing changes

    def test_open_filter_keeps_only_the_passing(self):
        _, result = self.run_query("kapanis>0 ml=evet ele=hayir", {"passed": True}, {"A.IS": 0.71, "B.IS": 0.32})
        self.assertEqual([m.symbol for m in result.matches], ["A.IS"])
        self.assertAlmostEqual(result.matches[0].values["ml_olasilik"], 0.71)
        self.assertIn("2 eşleşmeden 1 tanesi geçti", result.ml_note)


class DailyStepTest(unittest.TestCase):
    def test_follow_breaker_and_record(self):
        from core.signals import daily as book

        df = bars([(100, 100, 100, 100), (100, 101, 99.5, 100), (101, 104.5, 100, 104)])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "signals.db"
            text = book.run(date(2026, 11, 2), lambda s: df.iloc[:1], {"A.IS": df.iloc[:1]}, path,
                            enabled=lambda: True, probabilities=lambda frames: {"A.IS": 0.8})
            self.assertIn("Açık sinyal 1", text)
            off = book.run(date(2026, 11, 3), lambda s: df.iloc[:2], {"B.IS": df.iloc[:2]}, path,
                           enabled=lambda: False, probabilities=lambda frames: {"B.IS": 0.9})
            self.assertIn("Açık sinyal 1", off)  # a closed filter records nothing
            done = book.run(date(2026, 11, 4), lambda s: df, None, path, enabled=lambda: False)
            self.assertIn("kapanan 1", done)
            self.assertIn("hedefe ulaşan %100", done)

    def test_no_book_is_created_while_the_filter_is_off(self):
        # the PC install (03.11) caught the daily run creating data/signals.db with nothing to record
        from core.signals import daily as book

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "signals.db"
            self.assertEqual(book.run(date(2026, 11, 3), lambda s: None, None, path, enabled=lambda: False), "")
            self.assertFalse(path.exists())

    def test_durum_lines(self):
        from datetime import datetime
        from unittest import mock

        from core.reports import health

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "signals.db"
            empty = health.signal_book_lines(datetime(2026, 11, 3, 19), None, path)
            self.assertIn("Sanal kasa: 100.000 TL; sinyal defteri boş", empty[1])
            self.assertFalse(path.exists())
            S.connect(path).close()
            with mock.patch("core.ml.ml_filter.load", return_value=None):
                lines = health.signal_book_lines(datetime(2026, 11, 3, 19), None, path)
        self.assertIn("Sanal kasa: 100.000 TL", lines[1])
        self.assertIn("ML filtresi kapalı (ölçüm yok)", lines[2])


def hourly_bars(rows, first="2026-11-03 10:00"):
    index = pd.date_range(first, periods=len(rows), freq="h", tz="Europe/Istanbul")
    o, h, low, c = zip(*rows, strict=True)
    return pd.DataFrame({"open": o, "high": h, "low": low, "close": c, "volume": 1e5}, index=index)


class LiveTrackingTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "signals.db"

    def load(self, frames):
        from types import SimpleNamespace

        return lambda symbols: SimpleNamespace(frames={s: frames[s] for s in symbols if s in frames})

    def test_target_within_the_session(self):
        from core.signals import live

        conn = S.connect(self.path)
        S.add(conn, date(2026, 11, 2), "A.IS", 100.0)
        conn.close()
        before = pd.DataFrame({"open": [100.0], "high": [100.0], "low": [100.0], "close": [100.0], "volume": [1e5]},
                              index=pd.DatetimeIndex([pd.Timestamp("2026-11-02 17:00", tz="Europe/Istanbul")]))
        day = pd.concat([before, hourly_bars([(100, 100.5, 99.5, 100), (100, 101, 99, 100.5), (100.5, 104.2, 100, 104)])])
        lines = live.track(date(2026, 11, 3), self.path, load=self.load({"A.IS": day}))
        self.assertIn("A: hedefe ulaştı", lines[0].replace("Sanal sinyal ", ""))
        conn = S.connect(self.path)
        s = S.signals(conn)[0]
        conn.close()
        self.assertEqual((s.status, s.entry_price, s.exit_date), ("hedef", 100.0, date(2026, 11, 3)))
        self.assertEqual(lines[-1], S.DISCLAIMER)

    def test_hourly_never_expires_and_no_book_is_created(self):
        from core.signals import live

        self.assertEqual(live.track(date(2026, 11, 3), self.path, load=self.load({})), [])
        self.assertFalse(self.path.exists())
        conn = S.connect(self.path)
        S.add(conn, date(2026, 11, 2), "A.IS", 100.0)
        conn.close()
        flat = hourly_bars([(100, 100.5, 99.5, 100)] * 200)  # 25 sessions of hours, nothing hit
        live.track(date(2026, 12, 1), self.path, load=self.load({"A.IS": flat}))
        conn = S.connect(self.path)
        self.assertEqual(S.signals(conn)[0].status, "acik")  # only the daily close decides the expiry
        conn.close()

    def test_breaker_message_once(self):
        from core.signals import live

        conn = S.connect(self.path)
        for code in ("A.IS", "B.IS"):
            S.add(conn, date(2026, 11, 2), code, 100.0)
        conn.close()
        gap = hourly_bars([(100, 100, 100, 100), (70, 70, 70, 70)], first="2026-11-03 10:00")
        first = live.track(date(2026, 11, 3), self.path, load=self.load({"A.IS": gap, "B.IS": gap}))
        self.assertTrue(any("Şalter açıldı" in line for line in first))
        self.assertTrue(S.locked(date(2026, 11, 3), self.path))
        self.assertFalse(S.locked(date(2026, 11, 4), self.path))

    def test_in_session(self):
        from datetime import datetime

        from core.signals import live

        self.assertTrue(live.in_session(datetime(2026, 11, 3, 14, 5)))
        self.assertFalse(live.in_session(datetime(2026, 11, 3, 20, 0)))
        self.assertFalse(live.in_session(datetime(2026, 11, 7, 12, 0)))  # Saturday


class LockedScreenTest(unittest.TestCase):
    def test_tara_refuses_while_locked(self):
        import asyncio
        from types import SimpleNamespace
        from unittest import mock

        from bot import reports
        from tests.test_screen_telegram import fake_update

        sent = []
        with mock.patch("core.signals.store.locked", return_value=True):
            asyncio.run(reports.screen_cmd(fake_update(sent), SimpleNamespace(args=["rsi<30"])))
        self.assertEqual(sent[0][0], reports.LOCKED_TEXT)
        self.assertFalse(S.locked(date(2026, 11, 3), Path("/nonexistent/signals.db")))

