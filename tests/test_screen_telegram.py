"""
/tara Aşama 2: the Telegram side. /tara_alanlar, /tara_aciklama, /tara_devam, the inline
buttons (devam, karne, kaydet) and splitting long answers on whole lines.
"""

import asyncio
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from core.market.calendar import ISTANBUL
from core.screen import command, fields
from tests.test_screen import market

NOW = datetime(2026, 10, 28, 20, 0, tzinfo=ISTANBUL)
CHAT = 42


class Base(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.frames, self.bench = market()
        command.SESSIONS.clear()
        self.addCleanup(command.SESSIONS.clear)

    def kwargs(self):
        return dict(live=lambda symbols: (self.frames, self.bench), history_data=lambda: None,
                    signal_path=self.tmp / "s.csv", saved_path=self.tmp / "screens.csv", now=NOW, suspects=set())


class FieldsListTest(Base):
    def test_every_field_with_its_unit(self):
        text = command.fields_text()
        for name, f in fields.FIELDS.items():
            self.assertIn(name, text)
            self.assertIn(f.unit, text)
        for group in ("Trend", "Momentum", "Oynaklık", "Hacim", "Göreli güç", "Fiyat konumu"):
            self.assertIn(group, text)


class ExplainTest(Base):
    def test_each_condition_with_its_value_and_verdict(self):
        text = command.explain_text(["S00", "rsi<30", "ve", "ema20>ema50", "ve", "hacim_oran>100"], **self.kwargs())
        self.assertIn("S00", text)
        self.assertIn("✓ rsi<30", text)  # it fell hard
        self.assertIn("✗ hacim_oran>100", text)
        self.assertIn("ema20>ema50", text)
        self.assertIn("Sonuç: koşulların hepsi sağlanmıyor", text)
        self.assertTrue(text.rstrip().endswith(command.DISCLAIMER))

    def test_explains_why_a_stock_was_not_scanned(self):
        self.frames["OLD.IS"] = self.frames["S05.IS"].iloc[:-2]
        text = command.explain_text(["OLD", "rsi<30"], **self.kwargs())
        self.assertIn("taranmadı", text)
        self.assertIn("son kapanış", text)
        self.assertIn("Kullanım", command.explain_text(["S00"], **self.kwargs()))
        self.assertIn("bilinmeyen alan", command.explain_text(["S00", "rsx<30"], **self.kwargs()))
        self.assertIn("verisi yok", command.explain_text(["YOKBOYLE", "rsi<30"], **self.kwargs()))


class PagingTest(Base):
    def test_pages_of_fifteen_until_the_end(self):
        first = command.screen_text(["rsi>0", "likidite=0"], chat_id=CHAT, **self.kwargs())
        total = len(command.SESSIONS[CHAT].result.matches)
        self.assertEqual(total, 20)
        self.assertIn("(+5 hisse daha: /tara_devam)", first)
        more = command.more_text(CHAT)
        self.assertEqual(more.count("\n• "), 5)
        self.assertIn("16–20 / 20", more)
        self.assertIn("Liste bitti", command.more_text(CHAT))
        self.assertIn("Önce /tara", command.more_text(999))

    def test_card_and_save_hint(self):
        command.screen_text(["rsi>0"], chat_id=CHAT, **self.kwargs())
        self.assertIn("karne hesaplanamadı", command.card_text(CHAT))
        hint = command.save_hint(CHAT)
        self.assertIn("/tara_kaydet AD rsi>0", hint)
        self.assertIn("Önce /tara", command.card_text(999))


class SplitTest(unittest.TestCase):
    def test_long_answers_split_on_whole_lines(self):
        from bot.common import split_message

        lines = [f"• S{i:03d} " + "x" * 120 for i in range(80)]
        parts = split_message("\n".join(lines))
        self.assertGreater(len(parts), 1)
        self.assertTrue(all(len(p) <= 4096 for p in parts))
        self.assertEqual("".join(parts), "\n".join(lines))  # nothing lost
        self.assertTrue(all(p.endswith("\n") for p in parts[:-1]))  # every cut at a line end


def fake_update(sent, chat=CHAT, data=None):
    async def reply_text(text, **kw):
        sent.append((text, kw.get("reply_markup")))

    async def answer(*a, **k):
        sent.append(("<answer>", None))

    message = SimpleNamespace(reply_text=reply_text, chat=SimpleNamespace(id=chat))
    query = SimpleNamespace(data=data, answer=answer, message=message) if data else None
    return SimpleNamespace(message=message, effective_message=message, effective_chat=SimpleNamespace(id=chat),
                           callback_query=query)


class BotTest(Base):
    def test_commands_menu_and_buttons(self):
        from bot.handlers import COMMANDS, MENU
        from bot.reports import screen_button, screen_cmd

        for name in ("tara", "tara_alanlar", "tara_aciklama", "tara_devam", "tara_kaydet"):
            self.assertIn(name, dict(COMMANDS))
            self.assertIn(name, dict(MENU))
        sent = []
        real = command.screen_text
        with mock.patch.object(command, "screen_text",
                               side_effect=lambda words, chat_id: real(words, chat_id=chat_id, **self.kwargs())):
            asyncio.run(screen_cmd(fake_update(sent), SimpleNamespace(args=["rsi>0", "likidite=0"])))
        text, markup = sent[-1]
        labels = [b.text for row in markup.inline_keyboard for b in row]
        self.assertEqual(labels, ["Devam ▶", "Karne", "Kaydet"])
        self.assertEqual([b.callback_data for row in markup.inline_keyboard for b in row],
                         ["tara:devam", "tara:karne", "tara:kaydet"])
        for data, expected in (("tara:devam", "16–20 / 20"), ("tara:karne", "karne"), ("tara:kaydet", "/tara_kaydet")):
            got = []
            with mock.patch("bot.reports._allowed_chat", return_value=CHAT):
                asyncio.run(screen_button(fake_update(got, data=data), SimpleNamespace(args=[])))
            self.assertIn(expected, got[-1][0])

    def test_buttons_from_another_chat_are_ignored(self):
        from bot.reports import screen_button

        got = []
        with mock.patch("bot.reports._allowed_chat", return_value=CHAT):
            asyncio.run(screen_button(fake_update(got, chat=7, data="tara:devam"), SimpleNamespace(args=[])))
        self.assertEqual([t for t, _ in got if t != "<answer>"], [])

    def test_buttons_registered_for_the_allowed_chat_only(self):
        from telegram.ext import CallbackQueryHandler

        from bot.handlers import register_handlers

        added = []
        app = SimpleNamespace(add_handler=added.append, add_error_handler=lambda h: None)
        register_handlers(app, CHAT)
        callbacks = [h for h in added if isinstance(h, CallbackQueryHandler)]
        self.assertEqual(len(callbacks), 1)


if __name__ == "__main__":
    unittest.main()
