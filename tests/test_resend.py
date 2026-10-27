"""
/rapor_tekrar: a report that did not arrive (Telegram outage, deleted chat) is sent again from
logs/reports/ (written before every send since v0.57.0). /start shows buttons for the everyday
commands, and the Telegram "Menu" lists every command.
"""

import asyncio
import unittest
from datetime import date, datetime
from types import SimpleNamespace
from unittest import mock

from core.market.calendar import ISTANBUL
from core.reports import daily
from tests.test_bot_handlers import run

EVENING = datetime(2026, 10, 28, 20, 0, tzinfo=ISTANBUL)  # never the real clock: "27.10" means this year


class FixedClock(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(daily, "now_istanbul", return_value=EVENING)
        patcher.start()
        self.addCleanup(patcher.stop)


def save(day: date, text: str) -> None:
    daily.REPORT_TEXT_DIR.mkdir(parents=True, exist_ok=True)
    (daily.REPORT_TEXT_DIR / f"rapor_{day.isoformat()}.txt").write_text(text, encoding="utf-8")


class SavedReportTest(FixedClock):
    def test_latest_by_default_and_a_given_day(self):
        save(date(2026, 10, 27), "🗓 27.10 raporu")
        save(date(2026, 10, 28), "🗓 28.10 raporu")
        self.assertEqual(daily.saved_report(None), "🗓 28.10 raporu")
        self.assertEqual(daily.saved_report("27.10"), "🗓 27.10 raporu")
        self.assertEqual(daily.saved_report("27.10.2026"), "🗓 27.10 raporu")
        self.assertEqual(daily.saved_report("2026-10-27"), "🗓 27.10 raporu")

    def test_missing_day_lists_what_there_is(self):
        save(date(2026, 10, 27), "x")
        text = daily.saved_report("26.10")
        self.assertIn("26.10 için kayıtlı rapor yok", text)
        self.assertIn("27.10.2026", text)

    def test_nothing_saved_and_bad_input(self):
        self.assertIn("Kayıtlı rapor yok", daily.saved_report(None))
        self.assertIn("Tarih anlaşılmadı", daily.saved_report("dün"))

    def test_a_day_month_in_the_future_means_last_year(self):
        self.assertEqual(daily._parse_day("30.12", EVENING.date()), date(2025, 12, 30))

    def test_second_source_notes_are_not_reports(self):
        (daily.REPORT_TEXT_DIR).mkdir(parents=True, exist_ok=True)
        (daily.REPORT_TEXT_DIR / "ikinci_kaynak_2026-10-29.txt").write_text("not", encoding="utf-8")
        save(date(2026, 10, 28), "🗓 28.10 raporu")
        self.assertEqual(daily.saved_report(None), "🗓 28.10 raporu")


class ResendCommandTest(FixedClock):
    def test_command_sends_the_saved_text(self):
        from bot.reports import resend

        save(date(2026, 10, 28), "🗓 28.10 raporu")
        self.assertIn("🗓 28.10 raporu", run(resend))
        self.assertIn("🗓 28.10 raporu", run(resend, ["28.10"]))

    def test_registered(self):
        from bot.handlers import COMMANDS
        from bot.start import HELP_TEXT

        self.assertIn("rapor_tekrar", dict(COMMANDS))
        self.assertIn("/rapor_tekrar", HELP_TEXT)


class ButtonsTest(unittest.TestCase):
    def test_start_shows_buttons_for_registered_commands(self):
        from bot.handlers import COMMANDS
        from bot.start import start

        markups = []

        async def reply_text(text, reply_markup=None, **kwargs):
            markups.append(reply_markup)

        message = SimpleNamespace(reply_text=reply_text)
        asyncio.run(start(SimpleNamespace(message=message, effective_message=message), SimpleNamespace(args=[])))
        keyboard = next(m for m in markups if m is not None).keyboard
        labels = [b.text for row in keyboard for b in row]
        self.assertIn("/durum", labels)
        self.assertIn("/rapor_tekrar", labels)
        for label in labels:
            self.assertIn(label.lstrip("/"), dict(COMMANDS))

    def test_menu_lists_every_command_with_a_description(self):
        from bot.handlers import COMMANDS, MENU

        self.assertEqual({c for c, _ in MENU}, {c for c, _ in COMMANDS} - {"help"})
        self.assertTrue(all(text for _, text in MENU))


class MenuSetupTest(unittest.TestCase):
    def test_menu_is_sent_and_a_failure_never_stops_the_bot(self):
        from bot import application
        from bot.handlers import MENU

        sent = []

        async def ok(commands):
            sent.extend(commands)

        async def broken(commands):
            raise ConnectionError("telegram down")

        asyncio.run(application._set_menu(SimpleNamespace(bot=SimpleNamespace(set_my_commands=ok))))
        self.assertEqual([(c.command, c.description) for c in sent], list(MENU))
        asyncio.run(application._set_menu(SimpleNamespace(bot=SimpleNamespace(set_my_commands=broken))))  # no raise


if __name__ == "__main__":
    unittest.main()
