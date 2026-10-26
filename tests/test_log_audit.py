import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from core.market.calendar import ISTANBUL
from core.signals_log import audit_log, log_signal


def _at(m, d, hh, mm=0):
    return datetime(2026, m, d, hh, mm, tzinfo=ISTANBUL)


class AuditTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "signal_log.csv"

    def _log(self, day, logged, symbols=("AAA.IS", "BBB.IS")):
        for s in symbols:
            log_signal("daily", s, 50, "Nötr", day, path=self.path, now=logged)

    def test_missing_file_and_clean_log(self):
        self.assertEqual(audit_log(self.path).days, [])

        self._log(date(2026, 10, 26), _at(10, 26, 18, 30))
        self._log(date(2026, 10, 27), _at(10, 27, 18, 30))
        result = audit_log(self.path, now=_at(10, 27, 20))
        self.assertFalse(result.problems, result.text())
        self.assertEqual(result.rows, 4)

    def test_holiday_is_not_missing_but_a_skipped_session_is(self):
        self._log(date(2026, 10, 27), _at(10, 27, 18, 30))
        self._log(date(2026, 10, 28), _at(10, 28, 18, 30))  # half day
        # 29.10 holiday; 30.10 the computer was off
        self._log(date(2026, 11, 2), _at(11, 2, 18, 30))

        result = audit_log(self.path, now=_at(11, 2, 20))
        self.assertEqual(result.missing, [date(2026, 10, 30)])
        self.assertIn("kaydı olmayan 1 seans (30.10)", result.text())

    def test_records_from_stale_data_are_flagged(self):
        # Monday 06:47: Friday's close is the newest final one -> on time
        self._log(date(2026, 10, 23), _at(10, 26, 6, 47))
        self.assertEqual(audit_log(self.path, now=_at(10, 26, 7)).late, [])

        # Monday evening, but the store still had Friday's close
        self._log(date(2026, 10, 23), _at(10, 26, 18, 30), symbols=("CCC.IS",))
        result = audit_log(self.path, now=_at(10, 26, 20))
        self.assertEqual(result.late, [date(2026, 10, 23)])
        self.assertIn("eski veriyle", result.text())

    def test_duplicates_and_bad_rows(self):
        self._log(date(2026, 10, 26), _at(10, 26, 18, 30))
        self._log(date(2026, 10, 26), _at(10, 26, 18, 31), symbols=("AAA.IS",))
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write("bozuk,daily,XXX.IS,1,Nötr,2026-10-26,1,\n")
            fh.write("2026-10-26T18:30:00+03:00,daily,YYY.IS,1,Nötr,,1,\n")

        result = audit_log(self.path, now=_at(10, 26, 20))
        self.assertEqual((result.duplicates, result.bad_rows), (1, 2))
        self.assertTrue(result.problems)


class PerformanceReportTest(unittest.TestCase):
    def test_report_shows_log_health(self):
        from core.reports.forward import forward_report

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        text = forward_report(root / "signal_log.csv", root / "equity_log.csv", bars=lambda s: pd.DataFrame())
        self.assertIn("Kayıt sağlığı: günlük kayıt yok", text)


if __name__ == "__main__":
    unittest.main()
