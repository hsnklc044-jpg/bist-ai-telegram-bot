import asyncio
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from unittest import mock

from bot import notify
from core.market.calendar import ISTANBUL
from core.rotation import service
from tests.helpers import offline_market


def _at(day: str):
    return mock.patch.object(
        notify, "now_istanbul", return_value=datetime.fromisoformat(f"{day} 18:50").replace(
            tzinfo=ISTANBUL
        )
    )


class NotifyTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        patcher = mock.patch.object(service, "ROTATION_STATE_FILE", Path(tmp.name) / "s.json")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_friday_sends_weekly_report(self):
        # Synthetic prices end on Friday 2026-10-23 (not a month's first session).
        with offline_market(), _at("2026-10-23"):
            messages = notify.collect()

        self.assertEqual(len(messages), 1)
        self.assertIn("MOMENTUM ROTASYONU", messages[0])

    def test_quiet_on_other_days(self):
        with offline_market(), _at("2026-10-22"):
            self.assertEqual(notify.collect(), [])

    def test_report_on_demand(self):
        with offline_market():
            messages = notify.collect(report_now=True)

        self.assertIn("MOMENTUM ROTASYONU", messages[0])

    def test_dry_run_prints_without_token(self):
        out = io.StringIO()

        with offline_market(), redirect_stdout(out):
            notify.main(["--report", "--dry-run"])

        self.assertIn("MOMENTUM ROTASYONU", out.getvalue())

    def test_send_uses_configured_chat(self):
        sent = []

        class FakeBot:
            def __init__(self, token):
                self.token = token

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            async def send_message(self, chat_id, text):
                sent.append((self.token, chat_id, text))

        config = mock.Mock(bot_token="123:ABC", chat_id=777)

        with mock.patch.object(notify, "Bot", FakeBot), \
                mock.patch.object(notify, "require_bot_settings", return_value=config):
            asyncio.run(notify.send(["merhaba"]))

        self.assertEqual(sent, [("123:ABC", 777, "merhaba")])


if __name__ == "__main__":
    unittest.main()
