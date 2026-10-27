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
                mock.patch.object(daily.ping, "ping", side_effect=lambda url, fail=False: calls.append((url, fail))):
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
                mock.patch.object(daily.ping, "ping", side_effect=lambda url, fail=False: calls.append((url, fail))):
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
        sent.assert_called_once_with(URL)


class RedactTest(unittest.TestCase):
    def test_ping_addresses_are_hidden_in_the_install_proof(self):
        from core.reports import verify

        with mock.patch.dict("os.environ", {"HC_REPORT_URL": URL, "HC_BOT_URL": URL + "-bot"}):
            text = verify.redact(f"adres {URL} ve {URL}-bot")
        self.assertNotIn("1234abcd", text)


if __name__ == "__main__":
    unittest.main()
