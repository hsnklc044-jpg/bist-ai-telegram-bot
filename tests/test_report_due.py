"""
D11 (PC, 28.10.2026 half day): from 14:30 /durum said "KRİTİK · 28.10.2026 kapanış raporu gitmedi",
"fiyat verisi 1 seans geride", "canlı ölçüm kaydı olmayan seans" and the record-integrity SLO
warned, while the report runs at 18:30 on a half day too. The checks took the candle's close
(13:15 + 1:15 grace) as the deadline. Now one function answers "which session's report should
already have gone out" from the report schedule (18:30 + tolerance, session days only, half days
included), and the report, price, live-measurement and SLO checks all use it.
"""

import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from core.market.calendar import ISTANBUL, report_due_day
from core.reports import health, runs, slo
from core.signals_log import audit_log

HALF_DAY, HOLIDAY, NORMAL = date(2026, 10, 28), date(2026, 10, 29), date(2026, 10, 27)


def at(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=ISTANBUL)


class DueDayTest(unittest.TestCase):
    def test_the_schedule(self):
        self.assertEqual(report_due_day(at(HALF_DAY, 14, 30)), NORMAL)
        self.assertEqual(report_due_day(at(HALF_DAY, 18, 0)), NORMAL)
        self.assertEqual(report_due_day(at(HALF_DAY, 19, 44)), NORMAL)
        self.assertEqual(report_due_day(at(HALF_DAY, 19, 45)), HALF_DAY)
        self.assertEqual(report_due_day(at(NORMAL, 18, 0)), date(2026, 10, 26))
        self.assertEqual(report_due_day(at(NORMAL, 20, 0)), NORMAL)
        self.assertEqual(report_due_day(at(HOLIDAY, 21, 0)), HALF_DAY)  # the holiday expects nothing new
        self.assertEqual(report_due_day(at(date(2026, 10, 30), 12, 0)), HALF_DAY)  # Friday before its report
        self.assertEqual(health.due_session(at(HALF_DAY, 14, 30)), NORMAL)


class Files(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.runs = self.dir / "runs.csv"
        runs.record_run(at(NORMAL, 18, 30), runs.SENT, NORMAL, path=self.runs, now=at(NORMAL, 18, 34))


class ReportCheckTest(Files):
    def test_half_day_afternoon_and_evening(self):
        for moment in (at(HALF_DAY, 14, 30), at(HALF_DAY, 15, 55), at(HALF_DAY, 18, 0)):
            with self.subTest(moment=moment):
                self.assertEqual(health.report_check(moment, self.runs).state, health.OK)
        late = health.report_check(at(HALF_DAY, 19, 45), self.runs)
        self.assertEqual(late.state, health.CRIT)
        self.assertIn("28.10.2026 kapanış raporu gitmedi", late.text)

    def test_normal_day_and_holiday(self):
        self.assertEqual(health.report_check(at(NORMAL, 18, 0), self.runs).state, health.OK)
        runs.record_run(at(HALF_DAY, 18, 30), runs.SENT, HALF_DAY, path=self.runs, now=at(HALF_DAY, 18, 33))
        self.assertEqual(health.report_check(at(HOLIDAY, 21, 0), self.runs).state, health.OK)


class PriceCheckTest(unittest.TestCase):
    def bench(self, last: date):
        index = pd.bdate_range("2026-10-01", last)
        return lambda symbol: pd.DataFrame({"close": 1.0}, index=index)

    def test_prices_are_expected_with_the_report(self):
        self.assertEqual(health.price_check(at(HALF_DAY, 14, 30), self.bench(NORMAL)).state, health.OK)
        self.assertEqual(health.price_check(at(HALF_DAY, 18, 0), self.bench(NORMAL)).state, health.OK)
        behind = health.price_check(at(HALF_DAY, 20, 0), self.bench(NORMAL))
        self.assertEqual(behind.state, health.WARN)
        self.assertIn("1 seans geride", behind.text)


class LiveMeasurementTest(Files):
    def log(self, days):
        path = self.dir / "signal_log.csv"
        rows = ["logged_at,source,symbol,score,view,data_date,price,details"]
        rows += [f"{at(d, 18, 31).isoformat()},daily,THYAO.IS,50,nötr,{d.isoformat()},1,"
                 for d in days]
        path.write_text("\n".join(rows) + "\n", encoding="utf-8")
        return path

    def test_today_is_not_missing_before_the_report(self):
        path = self.log([date(2026, 10, 26), NORMAL])
        self.assertEqual(audit_log(path, at(HALF_DAY, 14, 30)).missing, [])
        self.assertEqual(audit_log(path, at(HALF_DAY, 20, 0)).missing, [HALF_DAY])
        result = slo.integrity(at(HALF_DAY, 15, 55), path, check_personal=False)
        self.assertEqual(result.state, slo.OK)

    def test_slo_window_counts_today_once_due(self):
        self.assertNotIn(HALF_DAY, slo._sessions(at(HALF_DAY, 18, 0)))
        self.assertIn(HALF_DAY, slo._sessions(at(HALF_DAY, 19, 45)))
        self.assertNotIn(HOLIDAY, slo._sessions(at(HOLIDAY, 21, 0)))


if __name__ == "__main__":
    unittest.main()
