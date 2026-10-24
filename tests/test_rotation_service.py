import asyncio
import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from core.backtest.runner import Dataset
from core.backtest.signals import score_history
from core.rotation import service
from tests.helpers import FakeProvider, make_ohlcv, offline_market


def _dataset(end: str) -> Dataset:
    prices = {f"S{i}.IS": make_ohlcv(rows=400, seed=i, end=end) for i in range(8)}

    return Dataset(
        prices=prices,
        signals={s: score_history(df) for s, df in prices.items()},
        benchmark=make_ohlcv(rows=400, seed=99, end=end),
        usdtry=None,
    )


class RotationServiceTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        patcher = mock.patch.object(service, "ROTATION_STATE_FILE", Path(tmp.name) / "s.json")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_report_ranks_by_momentum(self):
        data = _dataset("2026-10-23")
        report = service.build_report(data)

        self.assertEqual(len(report.picks), 5)
        self.assertEqual(len(report.reserves), 3)
        momenta = [p.momentum for p in report.picks + report.reserves]
        self.assertEqual(momenta, sorted(momenta, reverse=True))
        self.assertFalse(report.rebalance_today)
        self.assertEqual(report.next_rebalance, date(2026, 11, 2))
        self.assertIsNotNone(report.backtest)
        self.assertIn("MOMENTUM ROTASYONU", service.format_report(report))

    def test_notice_sent_once_on_first_session_of_month(self):
        self.assertIsNone(service.check_rebalance(_dataset("2026-10-23")))

        data = _dataset("2026-11-02")
        first = service.check_rebalance(data)
        again = service.check_rebalance(data)

        self.assertIn("AYLIK DENGELEME", first)
        self.assertIn("İlk bildirim", first)
        self.assertIsNone(again)
        self.assertEqual(service.load_state()["as_of"], "2026-11-02")

    def test_notice_lists_changes(self):
        report = service.build_report(_dataset("2026-11-02"), with_backtest=False)
        previous = [report.symbols[0], "OLD.IS"]

        text = service.format_rebalance(report, previous)

        self.assertIn("➖ Çıkan : OLD", text)
        self.assertIn(f"⏸ Kalan : {report.symbols[0].removesuffix('.IS')}", text)


class RotationBotTest(unittest.TestCase):
    def _run(self, handler, provider=None):
        sent: list[str] = []

        async def reply_text(text, **kwargs):
            sent.append(text)

        message = SimpleNamespace(reply_text=reply_text)
        update = SimpleNamespace(message=message, effective_message=message)

        with offline_market(provider):
            asyncio.run(handler(update, SimpleNamespace(args=[])))

        return sent

    def test_command(self):
        from bot.rotation import rotation

        sent = self._run(rotation)

        self.assertIn("MOMENTUM ROTASYONU", sent[-1])

    def test_command_without_data(self):
        from bot.rotation import NO_DATA, rotation

        sent = self._run(rotation, FakeProvider(fail=True))

        self.assertEqual(sent[-1], NO_DATA)

    def test_daily_job_is_scheduled(self):
        from telegram.ext import ApplicationBuilder

        from bot.application import schedule_jobs

        app = ApplicationBuilder().token("123:ABC").build()
        schedule_jobs(app, chat_id=777)

        jobs = app.job_queue.get_jobs_by_name("rebalance")
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].chat_id, 777)


if __name__ == "__main__":
    unittest.main()
