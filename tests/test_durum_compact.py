"""
K-70 madde 7 (v0.99.64): /durum shows a short summary — the healthy components counted on one line,
every problem on its own line, the SLOs in one line with the ones off target — and /durum tum the
full list. Nothing that needs attention is hidden.
"""

import asyncio
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest import mock

from core.reports import health
from core.reports.slo import SloResult

NOW = datetime(2026, 11, 4, 20, 0)
CHECKS = [health.Check("Telegram botu", health.OK, "çalışıyor"),
          health.Check("Fiyat verisi", health.OK, "güncel"),
          health.Check("Yedek", health.WARN, "02.11 eksik"),
          health.Check("Temel veri", health.INFO, "veri yok"),
          health.Check("Makro veri", health.UNKNOWN, "okunamadı")]
SLOS = [SloResult("Rapor teslimi", health.OK, 1.0, "1/1"), SloResult("Yedek", health.WARN, 0.667, "2/3"),
        SloResult("Veri doğruluğu", health.UNKNOWN, None, "kaynak yok")]


def report(full):
    with mock.patch.object(health, "health_checks", return_value=CHECKS), \
            mock.patch("core.reports.slo.measure", return_value=SLOS), \
            mock.patch.object(health, "signal_book_lines", return_value=["", "🧪 Sanal kasa: 100.000 TL"]):
        return health.health_report(NOW, full=full)


class CompactTest(unittest.TestCase):
    def test_short_summary_keeps_every_problem(self):
        text = report(full=False)
        self.assertIn("✅ 2 bileşen sağlıklı", text)
        self.assertNotIn("Telegram botu: çalışıyor", text)  # healthy ones are counted, not listed
        self.assertIn("Yedek: 02.11 eksik", text)
        self.assertIn("Makro veri: okunamadı", text)  # unknown is never hidden
        self.assertIn("Temel veri", text)  # information stays
        self.assertIn("📐 SLO: 1/3 hedefte, 1 ölçülemiyor; hedef dışı: Yedek %66,7", text)
        self.assertIn("🎯 Güvenilirlik", text)
        self.assertIn("🧪 Sanal kasa", text)
        self.assertIn("/durum tum", text)
        self.assertLess(len(text.splitlines()), len(report(full=True).splitlines()))

    def test_full_list_is_the_old_report(self):
        text = report(full=True)
        self.assertIn("Telegram botu: çalışıyor", text)
        self.assertIn("📐 SLO (son 7 gün)", text)

    def test_bot_command(self):
        from bot import reports
        from tests.test_screen_telegram import fake_update

        sent = []
        with mock.patch.object(reports, "health_report", side_effect=lambda full=False: f"full={full}"):
            asyncio.run(reports.status(fake_update(sent), SimpleNamespace(args=[])))
            asyncio.run(reports.status(fake_update(sent), SimpleNamespace(args=["tum"])))
        self.assertEqual([s[0] for s in sent], ["full=False", "full=True"])
