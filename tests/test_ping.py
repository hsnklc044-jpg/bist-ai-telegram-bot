"""
Outside monitoring (Healthchecks.io; user decision 27.10.2026). The ping addresses are secrets
in .env; without them nothing is sent. A ping never stops the report or the bot, and the
address never appears in a log or in verify_report.txt.
"""

import logging
import unittest
from types import SimpleNamespace
from unittest import mock

from core.infrastructure import ping

URL = "https://hc-ping.com/1234abcd-gizli-adres"


class PingTest(unittest.TestCase):
    def test_no_address_sends_nothing(self):
        get = mock.Mock()
        self.assertFalse(ping.ping("", get=get))
        get.assert_not_called()

    def test_success_and_fail(self):
        get = mock.Mock(return_value=SimpleNamespace(status_code=200))
        self.assertTrue(ping.ping(URL, get=get))
        self.assertTrue(ping.ping(URL, fail=True, get=get))
        self.assertEqual([c.args[0] for c in get.call_args_list], [URL, URL + "/fail"])

    def test_network_error_is_swallowed_and_the_address_is_not_logged(self):
        get = mock.Mock(side_effect=OSError("ağ yok " + URL))
        with self.assertLogs("core.infrastructure.ping", level=logging.WARNING) as logs:
            self.assertFalse(ping.ping(URL, get=get))
        self.assertNotIn("1234abcd", "\n".join(logs.output))


class NoRealPingInTestsTest(unittest.TestCase):
    def test_the_default_getter_is_offline_during_tests(self):
        with self.assertLogs("core.infrastructure.ping", level=logging.WARNING):
            self.assertFalse(ping.ping(URL))  # conftest: no network


class DailyReportPingTest(unittest.TestCase):
    def run_main(self, outcome):
        from core.reports import daily

        result = daily.DailyResult(day=__import__("datetime").date(2026, 10, 23), text="rapor", status=outcome)
        calls = []
        with mock.patch.dict("os.environ", {"HC_REPORT_URL": URL}), \
                mock.patch.object(daily, "_run", return_value=result), \
                mock.patch.object(daily.ping, "ping", side_effect=lambda url, fail=False, **k: calls.append((url, fail))):
            daily.main(["--send"])
        return calls

    def test_sent_skipped_and_holiday_are_success(self):
        for outcome in ("sent", "skipped", "holiday"):
            with self.subTest(outcome):
                self.assertEqual(self.run_main(outcome), [(URL, False)])

    def test_no_new_data_is_a_failure(self):
        self.assertEqual(self.run_main("stale"), [(URL, True)])

    def test_error_is_a_failure(self):
        from core.reports import daily

        calls = []
        with mock.patch.dict("os.environ", {"HC_REPORT_URL": URL}), \
                mock.patch.object(daily, "_run", side_effect=RuntimeError("bozuk")), \
                mock.patch.object(daily, "_notify_failure"), \
                mock.patch.object(daily.ping, "ping", side_effect=lambda url, fail=False, **k: calls.append((url, fail))):
            self.assertEqual(daily.main(["--send"]), 1)
        self.assertEqual(calls, [(URL, True)])

    def test_print_only_run_does_not_ping(self):
        from core.reports import daily

        result = daily.DailyResult(day=__import__("datetime").date(2026, 10, 23), text="rapor")
        with mock.patch.dict("os.environ", {"HC_REPORT_URL": URL}), \
                mock.patch.object(daily, "_run", return_value=result), \
                mock.patch.object(daily.ping, "ping") as sent:
            daily.main([])
        sent.assert_not_called()


class BotHeartbeatPingTest(unittest.TestCase):
    def test_heartbeat_also_pings(self):
        import asyncio

        from bot import scheduler

        with mock.patch.dict("os.environ", {"HC_BOT_URL": URL}), \
                mock.patch("core.reports.health.write_heartbeat"), \
                mock.patch.object(ping, "ping") as sent:
            asyncio.run(scheduler.heartbeat_job(SimpleNamespace()))
        sent.assert_called_once_with(URL, name=ping.BOT_ENV)  # the outcome is kept for /durum


class RedactTest(unittest.TestCase):
    def test_ping_addresses_are_hidden_in_the_install_proof(self):
        from core.reports import verify

        with mock.patch.dict("os.environ", {"HC_REPORT_URL": URL, "HC_BOT_URL": URL + "-bot"}):
            text = verify.redact(f"adres {URL} ve {URL}-bot")
        self.assertNotIn("1234abcd", text)


if __name__ == "__main__":
    unittest.main()


class MonitoringStatusTest(unittest.TestCase):
    """/durum shows whether outside monitoring is set up and whether the last pings arrived,
    never the address itself."""

    def setUp(self):
        import tempfile
        from pathlib import Path

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.state = Path(tmp.name) / "monitoring.json"
        from datetime import datetime

        from core.market.calendar import ISTANBUL

        self.now = datetime(2026, 10, 28, 21, 0, tzinfo=ISTANBUL)

    def check(self, env, pings=()):
        from core.reports import health

        with mock.patch.dict("os.environ", env, clear=False):
            for name, at, ok in pings:
                get = mock.Mock(return_value=SimpleNamespace(status_code=200 if ok else 500))
                ping.ping(URL, get=get, name=name, state_path=self.state, now=at)
            return health.monitoring_check(self.now, self.state)

    def test_ping_records_the_result_without_the_address(self):
        get = mock.Mock(return_value=SimpleNamespace(status_code=200))
        ping.ping(URL, fail=True, get=get, name=ping.REPORT_ENV, state_path=self.state, now=self.now)
        text = self.state.read_text(encoding="utf-8")
        self.assertIn('"fail": true', text)
        self.assertNotIn("1234abcd", text)

    def test_not_set_up_is_information_not_a_problem(self):
        from core.reports import health

        c = self.check({ping.REPORT_ENV: "", ping.BOT_ENV: ""})
        self.assertEqual(c.state, health.INFO)
        self.assertIn("kurulmadı", c.text)

    def test_both_set_and_recent_pings_arrived(self):
        from datetime import timedelta

        from core.reports import health

        c = self.check({ping.REPORT_ENV: URL, ping.BOT_ENV: URL},
                       [(ping.REPORT_ENV, self.now - timedelta(hours=2), True),
                        (ping.BOT_ENV, self.now - timedelta(minutes=3), True)])
        self.assertEqual(c.state, health.OK, c.text)
        self.assertNotIn("1234abcd", c.text)

    def test_failed_or_old_bot_ping_is_a_warning(self):
        from datetime import timedelta

        from core.reports import health

        c = self.check({ping.REPORT_ENV: URL, ping.BOT_ENV: URL},
                       [(ping.BOT_ENV, self.now - timedelta(minutes=3), False)])
        self.assertEqual(c.state, health.WARN)
        self.assertIn("ulaşmadı", c.text)
        old = self.check({ping.REPORT_ENV: URL, ping.BOT_ENV: URL},
                         [(ping.BOT_ENV, self.now - timedelta(hours=2), True)])
        self.assertEqual(old.state, health.WARN)

    def test_one_address_missing_is_a_warning(self):
        from core.reports import health

        c = self.check({ping.REPORT_ENV: "", ping.BOT_ENV: URL})
        self.assertEqual(c.state, health.WARN)
        self.assertIn("HC_REPORT_URL", c.text)

    def test_information_does_not_change_the_verdict_or_alert(self):
        from core.reports import health

        checks = [health.Check("A", health.OK, "x"), health.Check("Dışarıdan izleme", health.INFO, "kurulmadı")]
        self.assertEqual(health.verdict(checks), f"{health.OK} SAĞLIKLI: tüm kontroller geçti")
        from bot import scheduler

        self.assertEqual(scheduler.due_alerts(checks, self.now, self.state.with_name("alerts.json")), [])
