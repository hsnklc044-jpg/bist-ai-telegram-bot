import os
import threading
import time
import unittest
from datetime import date, datetime, timedelta
from unittest import mock

from core.market.calendar import ISTANBUL
from core.reports import daily, runs

DAY = date(2026, 10, 26)
CONFIG = mock.Mock(bot_token="T", chat_id=42)


class LockTest(unittest.TestCase):
    def test_second_holder_is_refused_until_release(self):
        with runs.report_lock():
            with self.assertRaises(runs.ReportBusy):
                with runs.report_lock():
                    pass
        self.assertFalse(runs.LOCK_FILE.exists())

        with runs.report_lock():  # free again
            pass

    def test_released_after_an_error(self):
        with self.assertRaises(ValueError):
            with runs.report_lock():
                raise ValueError("x")
        self.assertFalse(runs.LOCK_FILE.exists())

    def test_stale_lock_from_a_killed_run_expires(self):
        runs.LOCK_FILE.write_text("123 eski\n")
        old = time.time() - runs.STALE_AFTER.total_seconds() - 60
        os.utime(runs.LOCK_FILE, (old, old))

        with runs.report_lock():
            pass

    def test_concurrent_runs_do_the_work_once(self):
        done, busy = [], []
        start = threading.Barrier(2)

        def work():
            start.wait()
            try:
                with runs.report_lock():
                    time.sleep(0.2)  # e.g. filling paper orders
                    done.append(1)
            except runs.ReportBusy:
                busy.append(1)

        threads = [threading.Thread(target=work) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual((len(done), len(busy)), (1, 1))


class OncePerDataDayTest(unittest.TestCase):
    def _main(self, argv, sent):
        result = daily.DailyResult(DAY, f"rapor\n\n{daily.DISCLAIMER}")
        with mock.patch.object(daily, "build_daily", return_value=result), \
                mock.patch.object(daily, "_record_scores"), \
                mock.patch.object(daily, "_with_backup_line", side_effect=lambda t: t), \
                mock.patch.object(daily, "send_telegram", side_effect=lambda *a, **k: sent.append(a)), \
                mock.patch("core.infrastructure.settings.require_bot_settings", return_value=CONFIG):
            return daily.main(["--no-update", *argv])

    def test_same_data_day_is_sent_once(self):
        sent = []
        self.assertEqual(self._main(["--send"], sent), 0)
        self.assertEqual(self._main(["--send"], sent), 0)  # second scheduler, or a holiday

        self.assertEqual(len(sent), 1)
        self.assertEqual([r.status for r in runs.read_runs()], ["sent", "skipped"])
        self.assertTrue(runs.already_sent(DAY))

    def test_force_sends_again(self):
        sent = []
        self._main(["--send"], sent)
        self._main(["--send", "--force"], sent)
        self.assertEqual(len(sent), 2)

    def test_print_only_run_does_not_count_as_sent(self):
        sent = []
        self._main([], sent)
        self.assertFalse(runs.already_sent(DAY))
        self.assertEqual(runs.read_runs()[0].status, "built")

    def test_busy_run_is_skipped_and_recorded(self):
        sent = []
        with runs.report_lock():
            self.assertEqual(self._main(["--send"], sent), 0)

        self.assertEqual(sent, [])
        self.assertEqual(runs.read_runs()[0].status, "busy")

    def test_failure_is_recorded(self):
        with mock.patch.object(daily, "_run", side_effect=RuntimeError("Yahoo kapalı")):
            self.assertEqual(daily.main([]), 1)

        run = runs.read_runs()[0]
        self.assertEqual(run.status, "failed")
        self.assertIn("Yahoo kapalı", run.detail)


class RunLogTest(unittest.TestCase):
    def test_rows_round_trip(self):
        started = datetime(2026, 10, 26, 18, 30, tzinfo=ISTANBUL)
        runs.record_run(started, "sent", DAY, now=started + timedelta(minutes=2))

        row = runs.read_runs()[0]
        self.assertEqual((row.data_day, row.status), ("2026-10-26", "sent"))
        self.assertEqual(row.finished_at, "2026-10-26T18:32:00+03:00")


class ManualReportTest(unittest.TestCase):
    def test_report_command_waits_for_a_running_report(self):
        from bot.portfolio import _daily_text

        with runs.report_lock():
            text = _daily_text()

        self.assertIn("başka bir çalıştırmada", text)


if __name__ == "__main__":
    unittest.main()
