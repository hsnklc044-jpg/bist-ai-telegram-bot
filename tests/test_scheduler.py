import asyncio
import unittest
from datetime import time
from types import SimpleNamespace
from unittest import mock

from telegram.ext import ApplicationBuilder

from bot import scheduler
from core.market.calendar import ISTANBUL


def _app():
    return ApplicationBuilder().token("123:ABC").build()


class ReportTimeTest(unittest.TestCase):
    def test_parses_istanbul_time(self):
        self.assertEqual(scheduler.report_time("18:30"), time(18, 30, tzinfo=ISTANBUL))

    def test_unset_means_off(self):
        self.assertIsNone(scheduler.report_time(""))

    def test_rejects_garbage(self):
        with self.assertRaises(ValueError):
            scheduler.report_time("akşam")


class ScheduleTest(unittest.TestCase):
    def test_off_by_default(self):
        app = _app()

        with mock.patch.dict("os.environ", {scheduler.ENV: ""}):
            self.assertFalse(scheduler.schedule_daily_report(app))

        self.assertEqual(app.job_queue.get_jobs_by_name(scheduler.JOB_NAME), ())

    def test_weekday_job_when_set(self):
        app = _app()

        with mock.patch.dict("os.environ", {scheduler.ENV: "18:30"}):
            self.assertTrue(scheduler.schedule_daily_report(app))

        jobs = app.job_queue.get_jobs_by_name(scheduler.JOB_NAME)
        self.assertEqual(len(jobs), 1)

    def test_job_runs_the_daily_report_and_sends(self):
        with mock.patch("core.reports.daily.main", return_value=0) as run:
            asyncio.run(scheduler.daily_report_job(SimpleNamespace()))

        run.assert_called_once_with(["--send", "--log-dir", "logs"])


class ReportWatchTest(unittest.TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        patcher = mock.patch("core.config.paths.LOG_DIR", Path(tmp.name))
        patcher.start()
        self.addCleanup(patcher.stop)

    def _run(self, checks):
        from core.reports import health

        sent = []

        async def send_message(chat_id, text):
            sent.append((chat_id, text))

        context = SimpleNamespace(bot=SimpleNamespace(send_message=send_message), job=SimpleNamespace(chat_id=777))
        with mock.patch.object(health, "health_checks", return_value=checks):
            asyncio.run(scheduler.report_watch_job(context))
        return sent

    def test_registered_on_weekdays(self):
        app = _app()
        self.assertTrue(scheduler.schedule_report_watch(app, 777))
        self.assertEqual(len(app.job_queue.get_jobs_by_name(scheduler.WATCH_JOB)), 1)
        self.assertTrue(scheduler.schedule_heartbeat(app))
        self.assertEqual(len(app.job_queue.get_jobs_by_name(scheduler.HEARTBEAT_JOB)), 1)

    def test_silent_when_report_went_out(self):
        from core.reports import health

        self.assertEqual(self._run([health.Check("Günlük rapor", health.OK, "x")]), [])

    def test_warns_when_missing_or_unknown(self):
        from core.reports import health

        for state in (health.CRIT, health.WARN, health.UNKNOWN):
            with self.subTest(state=state):
                import shutil

                from core.config import paths

                shutil.rmtree(paths.LOG_DIR, ignore_errors=True)  # fresh alert state
                sent = self._run([health.Check("Günlük rapor", state, "x")])
                self.assertEqual(sent[0][0], 777)
                self.assertIn("Günlük rapor", sent[0][1])
                self.assertIn("Etkisi:", sent[0][1])
                self.assertIn("Yapılacak:", sent[0][1])

    def test_other_unknowns_only_in_durum(self):
        from core.reports import health

        self.assertEqual(self._run([health.Check("GitHub araştırması", health.UNKNOWN, "x")]), [])


class AlertDedupTest(unittest.TestCase):
    def test_same_problem_once_then_after_three_days(self):
        import tempfile
        from datetime import datetime
        from pathlib import Path

        from core.reports import health

        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "alerts.json"
            disk = [health.Check("Disk", health.WARN, "0.8 GB boş")]

            def at(day):
                return datetime(2026, 10, day, 20, tzinfo=ISTANBUL)

            self.assertEqual(len(scheduler.due_alerts(disk, at(26), state)), 1)
            self.assertEqual(scheduler.due_alerts(disk, at(27), state), [])  # not repeated
            self.assertEqual(scheduler.due_alerts(disk, at(28), state), [])
            self.assertEqual(len(scheduler.due_alerts(disk, at(29), state)), 1)  # reminder after 3 days

            worse = [health.Check("Disk", health.CRIT, "0.1 GB boş")]
            self.assertEqual(len(scheduler.due_alerts(worse, at(29), state)), 1)  # escalation is new

            ok = [health.Check("Disk", health.OK, "5 GB")]
            scheduler.due_alerts(ok, at(30), state)  # solved: forgotten
            self.assertEqual(len(scheduler.due_alerts(disk, at(30), state)), 1)  # comes back: sent again


if __name__ == "__main__":
    unittest.main()
