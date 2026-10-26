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
    def _run(self, state):
        from core.reports import health

        sent = []

        async def send_message(chat_id, text):
            sent.append((chat_id, text))

        context = SimpleNamespace(bot=SimpleNamespace(send_message=send_message), job=SimpleNamespace(chat_id=777))
        with mock.patch.object(health, "report_check", return_value=health.Check("Günlük rapor", state, "x")):
            asyncio.run(scheduler.report_watch_job(context))
        return sent

    def test_registered_on_weekdays(self):
        app = _app()
        self.assertTrue(scheduler.schedule_report_watch(app, 777))
        self.assertEqual(len(app.job_queue.get_jobs_by_name(scheduler.WATCH_JOB)), 1)

    def test_silent_when_report_went_out(self):
        from core.reports import health

        self.assertEqual(self._run(health.OK), [])

    def test_warns_when_missing_or_unknown(self):
        from core.reports import health

        for state in (health.WARN, health.UNKNOWN):
            sent = self._run(state)
            self.assertEqual(sent[0][0], 777)
            self.assertIn("Günlük rapor", sent[0][1])


if __name__ == "__main__":
    unittest.main()
