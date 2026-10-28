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


class Holidays2027Test(unittest.TestCase):
    """2027 (ileri hedefler): Kanun 2429'daki sabit günler ve Diyanet'in 2027 takvimi (Ramazan Bayramı
    9-11 Mart, arife 8 Mart; Kurban Bayramı 16-19 Mayıs, arife 15 Mayıs cumartesi). Borsa İstanbul'un
    kendi duyurusu Aralık 2026'da çıkar; o güne kadar yıl geçicidir."""

    def test_days(self):
        days = calendar.holidays()
        full = ["2027-01-01", "2027-03-09", "2027-03-10", "2027-03-11", "2027-04-23", "2027-05-17", "2027-05-18",
                "2027-05-19", "2027-07-15", "2027-08-30", "2027-10-29"]
        for d in full:
            with self.subTest(d=d):
                self.assertEqual(days[date.fromisoformat(d)].kind, "full")
        self.assertEqual(days[date(2027, 3, 8)].kind, "half")  # Ramazan Bayramı arifesi
        self.assertEqual(days[date(2027, 10, 28)].kind, "half")  # Cumhuriyet Bayramı arifesi
        self.assertEqual(len([d for d in days if d.year == 2027]), 13)  # 1 May, 15-16 May are weekends
        self.assertEqual(calendar.covered_until(), 2027)
        self.assertIn(2027, calendar.PROVISIONAL)

    def test_sessions(self):
        self.assertEqual(calendar.last_final_session_date(_at(2027, 3, 12, 9)), date(2027, 3, 8))
        self.assertEqual(calendar.last_final_session_date(_at(2027, 5, 20, 9)), date(2027, 5, 14))
        self.assertEqual(calendar.sessions_between(date(2027, 3, 5), date(2027, 3, 12)), 2)  # 8 (half), 12


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
        path.write_text("date,kind,name\n2026-01-01,full,Yılbaşı\n2026-01-05,full,Yanlış\n2026-12-31,half,x\n", encoding="utf-8")

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
        path.write_text("date,kind,name\n2026-01-01,full,Yılbaşı\n", encoding="utf-8")
        days = pd.bdate_range("2026-01-02", "2026-01-30")
        self.assertEqual(calendar.check_against_candles(days, path), [])

    def test_bad_kind_refused(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "h.csv"
        path.write_text("date,kind,name\n2026-01-01,closed,x\n", encoding="utf-8")
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
        self.assertIn("2027 geçici", check.text)

        december = health.calendar_check(_at(2026, 12, 10, 20))  # next year still provisional
        self.assertEqual(december.state, health.WARN)
        self.assertIn("Borsa İstanbul duyurusuyla teyit", december.text)
        self.assertEqual(health.calendar_check(_at(2027, 1, 4, 20)).state, health.WARN)  # in use, provisional
        self.assertEqual(health.calendar_check(_at(2028, 1, 3, 20)).state, health.UNKNOWN)

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
