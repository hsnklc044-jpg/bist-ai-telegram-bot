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


if __name__ == "__main__":
    unittest.main()
