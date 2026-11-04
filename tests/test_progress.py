"""
K-70 progress in /durum and the Friday report (v0.99.48): observed sessions out of 20, SLOs on target,
models validated, and "tam güvenilir" only when every criterion holds.
"""

import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

from core.reports import progress as P
from core.reports.health import OK, UNKNOWN, WARN
from core.reports.slo import SloResult

RUNS = ("started_at,finished_at,data_day,status,detail\n"
        "2026-10-30T18:30:00+03:00,2026-10-30T18:31:00+03:00,2026-10-30,sent,\n"   # before the new setup
        "2026-11-03T18:30:02+03:00,2026-11-03T18:36:23+03:00,2026-11-03,sent,\n"
        "2026-11-03T19:00:00+03:00,2026-11-03T19:01:00+03:00,2026-11-03,skipped,\n"  # same day again
        "2026-11-04T18:30:00+03:00,2026-11-04T18:31:00+03:00,,failed,x\n"
        "2026-11-05T18:30:00+03:00,2026-11-05T18:31:00+03:00,2026-11-05,sent,\n")


class ProgressTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.runs = self.dir / "runs.csv"
        self.runs.write_text(RUNS, encoding="utf-8")

    def test_observed_sessions_count_each_sent_day_once(self):
        self.assertEqual(P.observed_sessions(self.runs), 2)
        self.assertEqual(P.observed_sessions(self.dir / "yok.csv"), 0)

    def test_not_reliable_until_every_criterion_holds(self):
        results = [SloResult("Rapor teslimi", OK, 1.0, ""), SloResult("Veri doğruluğu", UNKNOWN, None, ""),
                   SloResult("Yedek", WARN, 0.6, "")]
        p = P.measure(datetime(2026, 11, 5, 20, 0), results, self.runs, self.dir)  # no validation reports
        self.assertFalse(p.reliable)
        text = "\n".join(P.lines(p))
        self.assertIn("gözlem 2/20 seans", text)
        self.assertIn("SLO 1/3", text)
        self.assertIn("model doğrulama 0/", text)
        self.assertIn("veri doğruluğu ölçülmedi", text)
        self.assertIn("tam güvenilir: hayır", text)

    def test_reliable_only_with_everything(self):
        from core.reports import validation

        for code in validation.HIGH_RISK:
            (self.dir / f"{code}.md").write_text(f"# {code}\nTarih: 2026-11-01\nKarar: kullanılabilir\n",
                                                 encoding="utf-8")
        rows = ["started_at,finished_at,data_day,status,detail"]
        rows += [f"x,y,{d:%Y-%m-%d},sent," for d in
                 (date(2026, 11, 3 + i) for i in range(28)) if d.weekday() < 5][:20]
        self.runs.write_text("\n".join(rows) + "\n", encoding="utf-8")
        results = [SloResult("Veri doğruluğu", OK, 0.995, ""), SloResult("Yedek", OK, 1.0, "")]
        p = P.measure(datetime(2026, 12, 2, 20, 0), results, self.runs, self.dir)
        self.assertTrue(p.reliable, p.missing)
        self.assertIn("tam güvenilir: evet", P.lines(p)[1])

    def test_durum_carries_the_line(self):
        from unittest import mock

        from core.reports import health

        with mock.patch.object(health, "health_checks", return_value=[]), \
                mock.patch("core.reports.slo.measure", return_value=[SloResult("Yedek", OK, 1.0, "")]), \
                mock.patch.object(health, "signal_book_lines", return_value=[]):
            text = health.health_report(datetime(2026, 11, 5, 20, 0))
        self.assertIn("🎯 Güvenilirlik (K-70)", text)
