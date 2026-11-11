"""Data trust levels (J, the user's 11.11.2026 decision). Written before the code.

Level 1 official or licensed, level 2 unofficial but checked against an independent second source, level 3 unofficial
and unchecked. A score, screen or filter carries the level of the weakest data it uses; a Telegram message built on
level 3 data gets one short line under its title; research can only say "geçti" on level 1 or 2 data."""

import asyncio
import json
import unittest
from datetime import date, datetime, timedelta
from unittest import mock

import pytest

from core.market import trust
from core.market.calendar import ISTANBUL

NOW = datetime(2026, 11, 11, 10, 0, tzinfo=ISTANBUL)


@pytest.fixture(autouse=True)
def _tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(trust, "SECOND_SOURCE_FILE", tmp_path / "price_second_source.json")
    trust.clear_cache()


def write_check(day: date, checked: int = 100, differing=(), source: str = "aracı kurum dosyası"):
    trust.SECOND_SOURCE_FILE.write_text(json.dumps({
        "date": day.isoformat(), "checked": checked, "differing": list(differing), "source": source,
    }), encoding="utf-8")


class LevelTest(unittest.TestCase):
    def test_the_weakest_data_sets_the_level(self):
        official = trust.Trust(1, "Borsa İstanbul resmî gün sonu")
        yahoo = trust.Trust(3, "Yahoo")
        self.assertEqual(trust.weakest(official, yahoo), yahoo)
        self.assertEqual(trust.weakest(official), official)
        self.assertEqual(trust.weakest(trust.Trust(2, "Yahoo, doğrulanmış"), official).level, 2)
        with self.assertRaises(ValueError):
            trust.weakest()

    def test_every_level_has_a_name(self):
        self.assertEqual(set(trust.LEVEL_NAMES), {1, 2, 3})
        self.assertIn("Seviye 3", trust.Trust(3, "Yahoo").label())
        self.assertIn("Yahoo", trust.Trust(3, "Yahoo").label())


class PriceTrustTest(unittest.TestCase):
    def test_yahoo_without_a_second_source_is_level_3(self):
        t = trust.price_trust(NOW)
        self.assertEqual(t.level, 3)
        self.assertIn("Yahoo", t.source)

    def test_a_fresh_clean_second_source_check_lifts_it_to_level_2(self):
        write_check(NOW.date() - timedelta(days=2))
        t = trust.price_trust(NOW)
        self.assertEqual(t.level, 2)
        self.assertIn("aracı kurum dosyası", t.source)

    def test_an_old_or_failing_check_leaves_it_at_level_3(self):
        write_check(NOW.date() - timedelta(days=20))
        self.assertEqual(trust.price_trust(NOW).level, 3)
        trust.clear_cache()
        write_check(NOW.date(), checked=100, differing=["A", "B"])  # 2 % differ, the SLO limit is 1 %
        self.assertEqual(trust.price_trust(NOW).level, 3)

    def test_a_broken_summary_file_never_raises(self):
        trust.SECOND_SOURCE_FILE.write_text("{bozuk", encoding="utf-8")
        self.assertEqual(trust.price_trust(NOW).level, 3)


class NoteTest(unittest.TestCase):
    def test_level_3_puts_one_short_line_under_the_title(self):
        y = trust.Trust(3, "Yahoo")
        self.assertEqual(trust.with_note("TEKNİK TABLO · 11.11\nsatır", y),
                         "TEKNİK TABLO · 11.11\nVeri: doğrulanmamış kaynak\nsatır")
        self.assertEqual(trust.with_note("tek satır", y), "tek satır\nVeri: doğrulanmamış kaynak")
        self.assertEqual(trust.NOTE, "Veri: doğrulanmamış kaynak")

    def test_level_1_and_2_add_nothing(self):
        for level in (1, 2):
            self.assertEqual(trust.with_note("A\nB", trust.Trust(level, "x")), "A\nB")

    def test_the_note_never_lands_inside_a_pre_block_or_twice(self):
        y = trust.Trust(3, "Yahoo")
        text = "<pre>A\nB</pre>\nalt"
        self.assertEqual(trust.with_note(text, y), "<pre>A\nB</pre>\nVeri: doğrulanmamış kaynak\nalt")
        once = trust.with_note("A\nB", y)
        self.assertEqual(trust.with_note(once, y), once)


class ResearchVerdictTest(unittest.TestCase):
    def test_only_level_1_or_2_data_can_pass(self):
        self.assertEqual(trust.research_verdict(True, trust.Trust(1, "BIST")), trust.PASSED)
        self.assertEqual(trust.research_verdict(True, trust.Trust(2, "Yahoo, doğrulanmış")), trust.PASSED)
        self.assertEqual(trust.research_verdict(True, trust.Trust(3, "Yahoo")), trust.PRELIMINARY)
        self.assertEqual(trust.research_verdict(False, trust.Trust(3, "Yahoo")), trust.FAILED)
        self.assertEqual(trust.PRELIMINARY, "ön bulgu")

    def test_the_research_report_says_so_on_level_3_data(self):
        line = trust.research_line(trust.Trust(3, "Yahoo"))
        self.assertIn("ön bulgu", line)
        self.assertIn("Seviye 3", line)
        self.assertIn("Seviye 1", trust.research_line(trust.Trust(1, "BIST")))
        import inspect

        from core.backtest import research

        self.assertIn("trust.research_line(", inspect.getsource(research))


class WiringTest(unittest.TestCase):
    def test_data_commands_carry_the_note_and_others_do_not(self):
        from bot import handlers

        names = {name for name, _ in handlers.COMMANDS}
        self.assertTrue(trust.DATA_COMMANDS <= names, trust.DATA_COMMANDS - names)
        for name in ("tablo", "karne", "uzun", "uzun_liste", "tara", "summary", "seviye"):
            self.assertIn(name, trust.DATA_COMMANDS)
        for name in ("otonom_dur", "otonom_devam", "help", "start", "durum", "panik"):
            self.assertNotIn(name, trust.DATA_COMMANDS)

    def test_the_bot_adds_the_note_once_inside_a_data_handler_only(self):
        from bot.application import RecordingBot

        sent = []

        async def fake_send(self, chat_id, text, *args, **kwargs):
            sent.append(text)
            return "ok"

        async def handler(update, context):
            await bot.send_message(1, "BAŞLIK\ngövde")
            await bot.send_message(1, "ikinci parça")

        with mock.patch("telegram.ext.ExtBot.send_message", fake_send), \
                mock.patch("core.infrastructure.outbox.record"):
            bot = RecordingBot(token="1:x")
            asyncio.run(trust.tagged(handler)(None, None))
            asyncio.run(bot.send_message(1, "BAŞLIK\nveri dışı"))
        self.assertEqual(sent, ["BAŞLIK\nVeri: doğrulanmamış kaynak\ngövde", "ikinci parça", "BAŞLIK\nveri dışı"])

    def test_registration_wraps_the_data_commands(self):
        from bot import handlers

        added = []
        app = mock.Mock()
        app.add_handler.side_effect = added.append
        handlers.register_handlers(app, chat_id=1)
        by_name = {next(iter(h.commands)): h.callback for h in added if hasattr(h, "commands")}
        self.assertTrue(getattr(by_name["tablo"], "trust_data", False))
        self.assertFalse(getattr(by_name["otonom_dur"], "trust_data", False))

    def test_jobs_and_the_daily_report_carry_the_note(self):
        import inspect

        from bot import scheduler
        from core.reports import daily

        source = inspect.getsource(scheduler)
        self.assertEqual(source.count("trust.data_message()"), 3)  # screens, hourly signals, portfolio health
        self.assertEqual(inspect.getsource(daily).count("data=True)"), 3)  # report, subscriptions, signal book

    def test_the_daily_sender_puts_the_note_under_the_title_on_level_3(self):
        from types import SimpleNamespace

        from core.reports import daily

        posted = []
        ok = SimpleNamespace(status_code=200, raise_for_status=lambda: None)

        def post(url, json=None, **k):
            posted.append(json["text"])
            return ok

        with mock.patch("core.infrastructure.outbox.record"):
            daily.send_telegram("AKŞAM RAPORU\nsatır", "1:x", 1, post=post, sleep=lambda s: None, data=True)
            daily.send_telegram("UYARI\nsatır", "1:x", 1, post=post, sleep=lambda s: None)
        self.assertEqual(posted, ["AKŞAM RAPORU\nVeri: doğrulanmamış kaynak\nsatır", "UYARI\nsatır"])

    def test_durum_shows_the_price_source_and_level(self):
        from core.reports import health

        line = health.data_trust_line(NOW)
        self.assertIn("Yahoo", line)
        self.assertIn("Seviye 3", line)
        import inspect

        self.assertIn("data_trust_line(", inspect.getsource(health.health_report))


if __name__ == "__main__":
    unittest.main()
