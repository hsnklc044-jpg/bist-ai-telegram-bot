"""
Road plan part 4 (operations): the weekly summary the bot sends by itself on Sunday, and the
monthly disaster recovery drill's latest result read from the research-results branch.
"""

import asyncio
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest import mock

from core.reports import weekly as W

NOW = datetime(2026, 11, 8, 18, 0)


def response(text, status=200):
    return SimpleNamespace(status_code=status, text=text)


class DrillTest(unittest.TestCase):
    def test_parse_success_and_failure(self):
        ok = W.parse_drill("DR drill 2026-11-03_07-45 (abc123): success\nrun: https://x/runs/1\n")
        self.assertEqual((ok.day.isoformat(), ok.passed), ("2026-11-03", True))
        bad = W.parse_drill("DR drill 2026-10-03_07-41 (abc): failure\n")
        self.assertFalse(bad.passed)
        self.assertIsNone(W.parse_drill("bozuk"))

    def test_line_states(self):
        get = lambda url, timeout: response("DR drill 2026-11-03_07-45 (abc): success\n")  # noqa: E731
        self.assertIn("✅ Felaket kurtarma tatbikatı: 03.11.2026 başarılı", W.drill_line(NOW, get))
        old = lambda url, timeout: response("DR drill 2026-09-03_07-45 (abc): success\n")  # noqa: E731
        self.assertIn("⚠️", W.drill_line(NOW, old))
        self.assertIn("eski", W.drill_line(NOW, old))
        failed = lambda url, timeout: response("DR drill 2026-11-03_07-45 (abc): failure\n")  # noqa: E731
        self.assertIn("❌", W.drill_line(NOW, failed))
        offline = lambda url, timeout: (_ for _ in ()).throw(OSError("yok"))  # noqa: E731
        self.assertIn("❔", W.drill_line(NOW, offline))
        missing = lambda url, timeout: response("", 404)  # noqa: E731
        self.assertIn("❔", W.drill_line(NOW, missing))


class SummaryTest(unittest.TestCase):
    def test_summary_has_version_slo_and_drill(self):
        import core
        from core.reports import slo

        results = [slo.SloResult("Rapor teslimi", slo.OK, 1.0, "5/5 seans")]
        with mock.patch.object(slo, "measure", return_value=results), \
                mock.patch.object(W, "drill_line", return_value="✅ Felaket kurtarma tatbikatı: 03.11.2026 başarılı"):
            text = W.summary(NOW)
        self.assertIn(f"v{core.__version__}", text)
        self.assertIn("📐 SLO (son 7 gün): 1/1 hedefte", text)
        self.assertIn("tatbikatı", text)

    def test_workflow_writes_latest(self):
        from pathlib import Path

        flow = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "dr-drill.yml").read_text(encoding="utf-8")
        self.assertIn("drills\\latest.txt", flow)


class JobTest(unittest.TestCase):
    def test_job_and_schedule(self):
        from telegram.ext import ApplicationBuilder

        from bot import scheduler

        sent = []

        async def send_message(chat_id, text):
            sent.append(text)

        context = SimpleNamespace(bot=SimpleNamespace(send_message=send_message), job=SimpleNamespace(chat_id=7))
        with mock.patch.object(W, "summary", return_value="🗒 özet"):
            asyncio.run(scheduler.weekly_summary_job(context))
        self.assertEqual(sent, ["🗒 özet"])
        app = ApplicationBuilder().token("123:abc").build()
        self.assertTrue(scheduler.schedule_weekly_summary(app, 7))
        self.assertEqual(len(app.job_queue.get_jobs_by_name(scheduler.WEEKLY_JOB)), 1)



class SentRecordAndWatchTest(unittest.TestCase):
    """05.11.2026: the summary watches everything but itself; a missing Sunday summary is a fault too."""

    def setUp(self):
        import tempfile
        from pathlib import Path

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "weekly_summary_sent.txt"

    def test_missing_after_sunday(self):
        monday = datetime(2026, 11, 9, 9, 0)
        self.assertIn("gönderilmedi", W.missing_warning(monday, self.path))  # never sent
        W.record_sent(datetime(2026, 11, 8, 18, 0, 5), self.path)
        self.assertIsNone(W.missing_warning(monday, self.path))
        W.record_sent(datetime(2026, 11, 1, 18, 0, 5), self.path)  # a later write of an older stamp
        self.assertIsNone(W.missing_warning(monday, self.path))  # the newest stamp counts
        next_monday = datetime(2026, 11, 16, 9, 0)
        self.assertIn("08.11.2026", W.missing_warning(next_monday, self.path))

    def test_watch_job_and_command(self):
        from telegram.ext import ApplicationBuilder

        from bot import handlers, scheduler

        sent = []

        async def send_message(chat_id, text):
            sent.append(text)

        context = SimpleNamespace(bot=SimpleNamespace(send_message=send_message), job=SimpleNamespace(chat_id=7))
        with mock.patch.object(W, "missing_warning", return_value="⚠️ yok"):
            asyncio.run(scheduler.weekly_watch_job(context))
        with mock.patch.object(W, "missing_warning", return_value=None):
            asyncio.run(scheduler.weekly_watch_job(context))
        self.assertEqual(sent, ["⚠️ yok"])
        with mock.patch.object(W, "summary", return_value="🗒 özet"), mock.patch.object(W, "record_sent") as rec:
            asyncio.run(scheduler.weekly_summary_job(context))
        rec.assert_called_once()
        app = ApplicationBuilder().token("123:abc").build()
        self.assertTrue(scheduler.schedule_weekly_summary(app, 7))
        self.assertEqual(len(app.job_queue.get_jobs_by_name(scheduler.WEEKLY_WATCH_JOB)), 1)
        self.assertIn("ozet", [name for name, _ in handlers.COMMANDS])


if __name__ == "__main__":
    unittest.main()
