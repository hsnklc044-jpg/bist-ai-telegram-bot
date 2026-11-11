"""Health alerts in the message style (H, the user's 11.11.2026 decision). Written before the code.

"❌ OLAY · saat" (a warning: "⚠️ UYARI · saat"), the state in one line, what is expected from the user (or that the bot
only reports), "/durum": at most four lines, no file path, command or JSON. The full guidance stays in /durum."""

import asyncio
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from bot import scheduler
from core.reports import style
from core.reports.health import CRIT, UNKNOWN, WARN, Check

NOW = datetime(2026, 11, 11, 20, 0)


class AlertTest(unittest.TestCase):
    def test_a_critical_check_is_an_event_in_four_lines(self):
        text = scheduler._alert_text(Check("Veri şeması", CRIT, "kayıtlar bu sürümle okunamıyor"), NOW)
        lines = text.splitlines()
        self.assertEqual(lines[0], "❌ OLAY · 20:00")
        self.assertEqual(lines[1], "Veri şeması: kayıtlar bu sürümle okunamıyor")
        self.assertTrue(lines[2].startswith("Senden beklenen: "))
        self.assertEqual(lines[-1], "/durum")
        self.assertEqual(style.problems(text, "uyari"), [])

    def test_a_warning_is_a_warning(self):
        text = scheduler._alert_text(Check("Fiyat verisi", WARN, "son kapanış 2 gün eski"), NOW)
        self.assertEqual(text.splitlines()[0], "⚠️ UYARI · 20:00")
        text = scheduler._alert_text(Check("Günlük rapor", UNKNOWN, "doğrulanamadı"), NOW)
        self.assertEqual(text.splitlines()[0], "⚠️ UYARI · 20:00")

    def test_a_technical_state_text_is_replaced_by_its_plain_impact(self):
        text = scheduler._alert_text(Check("Günlük rapor", CRIT, "logs/runs.csv: failed ConnectError"), NOW)
        self.assertNotIn("logs/", text)
        self.assertIn("günün raporu", text)
        self.assertEqual(style.forbidden(text), [])

    def test_every_check_has_a_plain_line(self):
        for name in scheduler.SEVERITY:
            text = scheduler._alert_text(Check(name, CRIT, "x"), NOW)
            self.assertEqual(style.problems(text, "uyari"), [], name)

    def test_a_job_failing_five_times_is_an_event_without_json(self):
        from core.infrastructure import retry as R

        sent = []

        async def send_message(chat_id, text):
            sent.append(text)

        async def no_wait(s):
            return None

        context = SimpleNamespace(bot=SimpleNamespace(send_message=send_message), job=SimpleNamespace(chat_id=7))
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch("core.signals.live.in_session", return_value=True), \
                mock.patch("core.signals.live.track", side_effect=OSError("Yahoo yanıt vermiyor")), \
                mock.patch.object(R, "STATE_FILE", Path(tmp) / "critical.json"), \
                mock.patch.object(R.asyncio, "sleep", no_wait):
            asyncio.run(scheduler.signal_track_job(context))
        self.assertEqual(len(sent), 1)
        lines = sent[0].splitlines()
        self.assertTrue(lines[0].startswith("❌ OLAY · "))
        self.assertIn("Saatlik takip", lines[1])
        self.assertEqual(lines[-1], "/durum")
        self.assertNotIn("{", sent[0])
        self.assertEqual(style.problems(sent[0], "uyari"), [])


if __name__ == "__main__":
    unittest.main()
