import os
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock

import pandas as pd

from core.market.calendar import ISTANBUL
from core.reports import health, runs
from core.signals_log import log_signal

# Monday 26.10.2026 20:00: Monday's report (data day 26.10) is due
MONDAY_EVENING = datetime(2026, 10, 26, 20, 0, tzinfo=ISTANBUL)
MONDAY_NOON = datetime(2026, 10, 26, 12, 0, tzinfo=ISTANBUL)


def _at(day, hh, mm=0):
    return datetime(2026, 10, day, hh, mm, tzinfo=ISTANBUL)


def _bench(last: str):
    index = pd.bdate_range(end=last, periods=5)
    return lambda symbol: pd.DataFrame({"close": 1.0}, index=index)


class ReportCheckTest(unittest.TestCase):
    def _record(self, started, status, day=None, detail=""):
        runs.record_run(started, status, day, detail, now=started)

    def test_no_records_is_unknown_not_ok(self):
        self.assertEqual(health.report_check(MONDAY_EVENING).state, health.UNKNOWN)

    def test_sent_today_is_ok(self):
        self._record(_at(26, 18, 30), "sent", date(2026, 10, 26))
        check = health.report_check(MONDAY_EVENING)
        self.assertEqual(check.state, health.OK)
        self.assertIn("26.10.2026 kapanışı", check.text)

    def test_missing_report_is_flagged(self):
        self._record(_at(23, 18, 30), "sent", date(2026, 10, 23))
        check = health.report_check(MONDAY_EVENING)
        self.assertEqual(check.state, health.CRIT)
        self.assertIn("26.10.2026 kapanış raporu gitmedi", check.text)

    def test_not_due_before_the_evening(self):
        # Friday's report went out on Monday morning (computer was off on Friday)
        self._record(_at(26, 6, 47), "sent", date(2026, 10, 23))
        self.assertEqual(health.report_check(MONDAY_NOON).state, health.OK)

    def test_holiday_run_counts_as_done(self):
        self._record(_at(23, 18, 30), "sent", date(2026, 10, 23))
        self._record(_at(26, 18, 30), "skipped", date(2026, 10, 23))  # no new candle
        self.assertEqual(health.report_check(MONDAY_EVENING).state, health.OK)

    def test_latest_failure_is_shown(self):
        self._record(_at(23, 18, 30), "sent", date(2026, 10, 23))
        self._record(_at(26, 18, 30), "failed", detail="ConnectionError: Yahoo")
        check = health.report_check(MONDAY_EVENING)
        self.assertEqual(check.state, health.CRIT)
        self.assertIn("Yahoo", check.text)


class DataChecksTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def test_prices_current_and_behind(self):
        self.assertEqual(health.price_check(MONDAY_EVENING, _bench("2026-10-26")).state, health.OK)
        behind = health.price_check(MONDAY_EVENING, _bench("2026-10-22"))
        self.assertEqual(behind.state, health.WARN)
        self.assertIn("2 seans geride", behind.text)

    def test_prices_unreadable_is_unknown(self):
        def broken(symbol):
            raise OSError("db")

        self.assertEqual(health.price_check(MONDAY_EVENING, broken).state, health.UNKNOWN)
        self.assertEqual(health.price_check(MONDAY_EVENING, lambda s: pd.DataFrame()).state, health.UNKNOWN)

    def test_signal_log_counts_and_duplicates(self):
        path = self.root / "signal_log.csv"
        self.assertEqual(health.signal_check(path, MONDAY_NOON).state, health.UNKNOWN)

        for day, logged in ((date(2026, 10, 22), _at(22, 18, 30)), (date(2026, 10, 23), _at(23, 18, 30))):
            for symbol in ("AAA.IS", "BBB.IS"):
                log_signal("daily", symbol, 50, "Nötr", day, path=path, now=logged)
        log_signal("analyze", "AAA.IS", 50, "Nötr", date(2026, 10, 23), path=path, now=_at(23, 19))

        check = health.signal_check(path, MONDAY_NOON)
        self.assertEqual(check.state, health.OK, check.text)
        self.assertIn("2 gün, 4 kayıt; 22.10.2026 – 23.10.2026", check.text)

        log_signal("daily", "AAA.IS", 50, "Nötr", date(2026, 10, 23), path=path, now=_at(23, 19))
        check = health.signal_check(path, MONDAY_NOON)
        self.assertEqual(check.state, health.WARN)
        self.assertIn("1 tekrar kayıt", check.text)

    def test_equity(self):
        path = self.root / "equity_log.csv"
        self.assertEqual(health.equity_check(path).state, health.UNKNOWN)
        path.write_text("date,account,value,cash,invested,positions\n2026-10-23,paper,100000.00,100000.00,0.00,0\n", encoding="utf-8")
        check = health.equity_check(path)
        self.assertEqual(check.state, health.OK)
        self.assertIn("23.10.2026: 100.000 TL", check.text)

    def test_backup_age(self):
        self.assertEqual(health.backup_check(MONDAY_EVENING, self.root).state, health.UNKNOWN)

        zip_path = self.root / "quantbist_2026-10-26.zip"
        zip_path.write_bytes(b"x")
        stamp = _at(26, 6, 47).timestamp()
        os.utime(zip_path, (stamp, stamp))
        self.assertEqual(health.backup_check(MONDAY_EVENING, self.root).state, health.OK)

        old = _at(20, 18, 30).timestamp()
        os.utime(zip_path, (old, old))
        self.assertEqual(health.backup_check(MONDAY_EVENING, self.root).state, health.WARN)


class ReportTextTest(unittest.TestCase):
    def test_verdict_never_ok_with_unknowns(self):
        checks = [health.Check("A", health.OK, "x"), health.Check("B", health.UNKNOWN, "y")]
        with mock.patch.object(health, "health_checks", return_value=checks):
            text = health.health_report(MONDAY_EVENING)

        self.assertIn("BİLİNMİYOR", text)
        self.assertNotIn("SAĞLIKLI: tüm kontroller geçti", text)
        self.assertIn("❔ BİLİNMİYOR · B: y", text)

    def test_all_ok(self):
        with mock.patch.object(health, "health_checks", return_value=[health.Check("A", health.OK, "x")]):
            self.assertIn("SAĞLIKLI: tüm kontroller geçti", health.health_report(MONDAY_EVENING))


if __name__ == "__main__":
    unittest.main()
