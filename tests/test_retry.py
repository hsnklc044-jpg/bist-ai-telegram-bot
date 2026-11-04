"""
Retry with exponential backoff and a critical alert (v0.99.49, the user's "auto-healing" request):
transient errors (network, timeout, a locked database) are retried after 2, 4, 8 and 16 s; anything
else is not retried; when every attempt fails a JSON payload goes to Telegram once per job and error
type in 6 hours. The bot never stops on it.
"""

import asyncio
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from core.infrastructure import retry as R


def run(coro):
    return asyncio.run(coro)


class RetryTest(unittest.TestCase):
    def setUp(self):
        self.waits = []

        async def sleep(s):
            self.waits.append(s)

        self.sleep = sleep

    def test_a_transient_error_is_retried_then_succeeds(self):
        calls = iter([OSError("ağ"), sqlite3.OperationalError("database is locked"), "tamam"])

        def fn():
            x = next(calls)
            if isinstance(x, Exception):
                raise x
            return x

        self.assertEqual(run(R.retry(fn, name="iş", sleep=self.sleep)), "tamam")
        self.assertEqual(self.waits, [2, 4])

    def test_every_attempt_fails(self):
        def fn():
            raise TimeoutError("zaman aşımı")

        with self.assertRaises(R.RetryExhausted) as ctx:
            run(R.retry(fn, name="saatlik takip", sleep=self.sleep))
        self.assertEqual(self.waits, [2, 4, 8, 16])  # 5 attempts in about 30 s
        self.assertEqual(ctx.exception.attempts, 5)
        self.assertIsInstance(ctx.exception.last, TimeoutError)

    def test_a_bug_is_not_retried(self):
        def fn():
            raise ValueError("hata")

        with self.assertRaises(ValueError):
            run(R.retry(fn, name="iş", sleep=self.sleep))
        self.assertEqual(self.waits, [])


class AlertTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.state = Path(tmp.name) / "critical.json"

    def test_payload_is_json(self):
        exc = R.RetryExhausted("saatlik takip", 5, OSError("ağ yok"))
        payload = json.loads(R.payload(exc, datetime(2026, 11, 4, 11, 0)))
        self.assertEqual(payload["seviye"], "KRİTİK")
        self.assertEqual(payload["is"], "saatlik takip")
        self.assertEqual(payload["deneme"], 5)
        self.assertEqual(payload["hata"], "OSError: ağ yok")
        self.assertEqual(payload["zaman"], "2026-11-04T11:00:00")

    def test_same_problem_alerts_once_in_six_hours(self):
        now = datetime(2026, 11, 4, 11, 0)
        exc = R.RetryExhausted("saatlik takip", 5, OSError("x"))
        self.assertTrue(R.should_alert(exc, now, self.state))
        self.assertFalse(R.should_alert(exc, now + timedelta(hours=1), self.state))
        self.assertTrue(R.should_alert(exc, now + timedelta(hours=7), self.state))
        other = R.RetryExhausted("yedek", 5, OSError("x"))
        self.assertTrue(R.should_alert(other, now + timedelta(hours=1), self.state))


class JobTest(unittest.TestCase):
    def test_hourly_tracking_retries_and_alerts(self):
        from bot import scheduler

        sent = []

        async def send_message(chat_id, text):
            sent.append(text)

        async def no_wait(s):
            return None

        context = SimpleNamespace(bot=SimpleNamespace(send_message=send_message), job=SimpleNamespace(chat_id=7))
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch("core.signals.live.in_session", return_value=True), \
                mock.patch("core.signals.live.track", side_effect=OSError("Yahoo yanıt vermiyor")) as track, \
                mock.patch.object(R, "STATE_FILE", Path(tmp) / "critical.json"), \
                mock.patch.object(R.asyncio, "sleep", no_wait):
            asyncio.run(scheduler.signal_track_job(context))  # never raises
            self.assertEqual(track.call_count, 5)
            self.assertTrue(track.call_args.kwargs.get("strict"))
        self.assertEqual(len(sent), 1)
        self.assertIn("🚨", sent[0])
        self.assertIn('"is": "saatlik takip"', sent[0])
