import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from core.market import calendar
from core.market.calendar import ISTANBUL


def _at(y, m, d, hh, mm=0):
    return datetime(y, m, d, hh, mm, tzinfo=ISTANBUL)


class HolidayFileTest(unittest.TestCase):
    def test_2026_file(self):
        days = calendar.holidays()
        self.assertEqual(days[date(2026, 10, 29)].kind, "full")
        self.assertEqual(days[date(2026, 10, 28)].kind, "half")
        self.assertTrue(all(d.weekday() < 5 for d in days))  # weekends are not listed
        self.assertGreaterEqual(calendar.covered_until(), 2026)

    def test_session_days(self):
        self.assertFalse(calendar.is_session_day(date(2026, 10, 29)))  # Cumhuriyet Bayramı
        self.assertTrue(calendar.is_session_day(date(2026, 10, 28)))  # half day still trades
        self.assertFalse(calendar.is_session_day(date(2026, 10, 31)))  # Saturday
        self.assertEqual(calendar.sessions_between(date(2026, 10, 27), date(2026, 11, 2)), 3)  # 28, 30, 2


class LastFinalSessionTest(unittest.TestCase):
    def test_half_day_is_final_after_midday(self):
        self.assertEqual(calendar.last_final_session_date(_at(2026, 10, 28, 12, 0)), date(2026, 10, 27))
        self.assertEqual(calendar.last_final_session_date(_at(2026, 10, 28, 14, 0)), date(2026, 10, 28))

    def test_holiday_rolls_back(self):
        self.assertEqual(calendar.last_final_session_date(_at(2026, 10, 29, 20, 0)), date(2026, 10, 28))
        self.assertEqual(calendar.last_final_session_date(_at(2026, 10, 30, 9, 0)), date(2026, 10, 28))
        # Kurban Bayramı 27-29 May, then the weekend
        self.assertEqual(calendar.last_final_session_date(_at(2026, 5, 31, 12, 0)), date(2026, 5, 26))

    def test_normal_days_unchanged(self):
        self.assertEqual(calendar.last_final_session_date(_at(2026, 10, 26, 18, 0)), date(2026, 10, 23))
        self.assertEqual(calendar.last_final_session_date(_at(2026, 10, 26, 18, 30)), date(2026, 10, 26))


class CheckAgainstCandlesTest(unittest.TestCase):
    def test_reports_mismatches(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "h.csv"
        path.write_text("date,kind,name\n2026-01-01,full,Yılbaşı\n2026-01-05,full,Yanlış\n2026-12-31,half,x\n")

        days = pd.bdate_range("2026-01-02", "2026-01-09")
        days = days.drop([pd.Timestamp("2026-01-07")])  # unknown gap
        problems = calendar.check_against_candles(days, path)

        self.assertTrue(any("2026-01-05: dosyada tatil" in p for p in problems))
        self.assertTrue(any("2026-01-07: hafta içi" in p for p in problems))
        self.assertEqual(len(problems), 2)

    def test_consistent(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "h.csv"
        path.write_text("date,kind,name\n2026-01-01,full,Yılbaşı\n")
        days = pd.bdate_range("2026-01-02", "2026-01-30")
        self.assertEqual(calendar.check_against_candles(days, path), [])

    def test_bad_kind_refused(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "h.csv"
        path.write_text("date,kind,name\n2026-01-01,closed,x\n")
        with self.assertRaises(ValueError):
            calendar.holidays(path)


class NotSentReasonTest(unittest.TestCase):
    def test_reasons(self):
        from core.reports.daily import _not_sent_reason

        status, note = _not_sent_reason(date(2026, 10, 28), _at(2026, 10, 29, 18, 30))
        self.assertEqual((status, note), ("holiday", "Cumhuriyet Bayramı"))

        status, note = _not_sent_reason(date(2026, 10, 23), _at(2026, 10, 26, 18, 30))
        self.assertEqual(status, "stale")
        self.assertIn("beklenen 26.10.2026", note)

        self.assertEqual(_not_sent_reason(date(2026, 10, 26), _at(2026, 10, 26, 18, 31))[0], "skipped")


class HealthCalendarTest(unittest.TestCase):
    def test_upcoming_and_coverage(self):
        from core.reports import health

        check = health.calendar_check(_at(2026, 10, 26, 20))
        self.assertEqual(check.state, health.OK)
        self.assertIn("28.10 Cumhuriyet Bayramı arifesi (yarım gün)", check.text)
        self.assertIn("29.10 Cumhuriyet Bayramı", check.text)

        self.assertEqual(health.calendar_check(_at(2026, 12, 10, 20)).state, health.WARN)
        self.assertEqual(health.calendar_check(_at(2027, 1, 4, 20)).state, health.UNKNOWN)

    def test_holiday_run_counts_and_stale_is_flagged(self):
        from core.reports import health, runs

        runs.record_run(_at(2026, 10, 28, 18, 30), "sent", date(2026, 10, 28), now=_at(2026, 10, 28, 18, 31))
        runs.record_run(_at(2026, 10, 29, 18, 30), "holiday", date(2026, 10, 28), "Cumhuriyet Bayramı",
                        now=_at(2026, 10, 29, 18, 31))
        self.assertEqual(health.report_check(_at(2026, 10, 29, 20)).state, health.OK)

        runs.record_run(_at(2026, 10, 30, 18, 30), "stale", date(2026, 10, 28), "beklenen 30.10.2026 kapanışı",
                        now=_at(2026, 10, 30, 18, 31))
        check = health.report_check(_at(2026, 10, 30, 20))
        self.assertEqual(check.state, health.WARN)
        self.assertIn("verisi gelmedi", check.text)


if __name__ == "__main__":
    unittest.main()
