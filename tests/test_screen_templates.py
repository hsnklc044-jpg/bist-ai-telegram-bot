"""
Ready-made /tara templates from the user's TradingView screens (görev 28.10, Aşama B). Filter
templates, not advice: fixed in code (never tuned on results), apart from the user's saved
screens, each with its source, the conditions left out (no fundamental data) and a history card
computed in advance (a /tara call never waits for it).
"""

import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from core.screen import command, templates
from core.screen.language import parse
from tests.test_screen import market

EXPECTED = {
    "basit_teknik": "goreli_hacim>1 kesti_yukari(rsi,50) kesti_yukari(ema5,ema20)",
    "basit_teknik_3g": "goreli_hacim>1 son(3,kesti_yukari(rsi,50)) son(3,kesti_yukari(ema5,ema20))",
    "bebek_teknik": "goreli_hacim>1 momentum10>0",
    "duseni_kiran": "kapanis<zirve_1a rsi 50..70 goreli_hacim>1.5 ema5>ema10 ema10>ema20 ema20>ema40 "
                    "ema50>ema100 ema100>ema200 vwma20<kapanis degisim_1h<15 degisim_1a<20 cci>-100 kapanis>acilis",
    "tek_tus_trend": "kapanis>ema50 ema50>ema200 rsi 60..70 adx>20 ortalama_hacim_30g>10000000 degisim_1a<30 "
                     "ema20<kapanis degisim_3a<60",
    "teknik_temel_ema": "kapanis>ema50 ema50>ema200",
}


class DefinitionTest(unittest.TestCase):
    def test_exactly_the_given_conditions(self):
        self.assertEqual({k: t.criteria for k, t in templates.TEMPLATES.items()}, EXPECTED)
        for name, t in templates.TEMPLATES.items():
            with self.subTest(name):
                parse(t.criteria)  # every template is valid /tara
                self.assertIn("kullanıcının TradingView taraması", t.source)

    def test_left_out_conditions_are_named(self):
        self.assertIn("piyasa değeri", templates.TEMPLATES["bebek_teknik"].skipped)
        self.assertIn("FSO", templates.TEMPLATES["bebek_teknik"].skipped)
        self.assertIn("beta", templates.TEMPLATES["tek_tus_trend"].skipped)
        self.assertIn("gelir artışı", templates.TEMPLATES["teknik_temel_ema"].skipped)
        self.assertEqual(templates.TEMPLATES["duseni_kiran"].skipped, "—")

    def test_no_praise_words(self):
        for name, t in templates.TEMPLATES.items():
            text = f"{name} {t.title} {t.source}".lower()
            for word in ("şampiyon", "sampiyon", "en iyi", "fırsat", r"\bal\b", "güçlü al"):
                self.assertIsNone(re.search(word, text), (name, word))

    def test_templates_are_not_research_candidates(self):
        text = (Path(__file__).resolve().parents[1] / "docs" / "RESEARCH_PROGRAM.md").read_text(encoding="utf-8")
        for name in templates.TEMPLATES:
            self.assertNotIn(name, text)


class CommandTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.frames, self.bench = market()

    def test_list(self):
        text = templates.list_text(cards={})
        for name, t in templates.TEMPLATES.items():
            self.assertIn(f"/tara {name}", text)
            self.assertIn(t.criteria, text)
        self.assertIn("karne hazırlanıyor", text)
        self.assertIn("Filtre sonucudur, yatırım önerisi değildir.", text)

    def test_list_shows_a_ready_card(self):
        from core.screen.card import CardStats

        stats = {5: CardStats(n=500, independent=80, mean=0.001, median=0.0, hit=0.5, low=-0.004, high=0.006,
                              without_top=0.0), 20: CardStats(n=12)}
        text = templates.list_text(cards={"bebek_teknik": stats})
        self.assertIn("ayırt edilemiyor", text)

    def test_runs_by_name_and_wins_over_nothing(self):
        text = command.screen_text(["bebek_teknik"], live=lambda s: (self.frames, self.bench), history_data=lambda: None,
                                   signal_path=self.tmp / "s.csv", saved_path=self.tmp / "screens.csv",
                                   suspects=set())
        self.assertIn("/tara goreli_hacim>1 ve momentum10>0", text)
        self.assertIn("şablon: bebek_teknik", text)

    def test_a_saved_screen_cannot_take_a_template_name(self):
        self.assertIn("şablon", command.save_text(["duseni_kiran", "rsi<30"], path=self.tmp / "screens.csv"))

    def test_cards_are_computed_in_advance_without_blocking(self):
        with mock.patch.object(command.C, "cached_history", return_value={}) as computed:
            templates.warm(load=lambda: None)
        self.assertEqual(computed.call_count, len(templates.TEMPLATES))
        with mock.patch.object(command.C, "peek", return_value=None) as peeked:
            templates.list_text()
        self.assertEqual(peeked.call_count, len(templates.TEMPLATES))  # reads the cache only


class CardsTextTest(unittest.TestCase):
    def test_every_template_on_given_data(self):
        frames, bench = market()
        text = templates.cards_text(load=lambda: (frames, bench, None))
        for name in templates.TEMPLATES:
            self.assertIn(f"{name}: ", text)
        self.assertIn("maliyet dahil", text)

    def test_main_and_warm_thread(self):
        import io
        from contextlib import redirect_stdout

        from bot import application

        with mock.patch.object(templates, "cards_text", return_value="karneler"), redirect_stdout(io.StringIO()) as out:
            self.assertEqual(templates.main([]), 0)
        self.assertIn("karneler", out.getvalue())
        done = []
        with mock.patch.object(templates, "warm", side_effect=lambda: done.append(1)):
            application._warm_templates()
            import threading

            for t in threading.enumerate():
                if t.name == "tara-templates":
                    t.join(5)
        self.assertEqual(done, [1])


class BotTest(unittest.TestCase):
    def test_command_and_help(self):
        from bot.handlers import COMMANDS, MENU
        from bot.start import HELP_TEXT

        self.assertIn("tara_sablonlar", dict(COMMANDS))
        self.assertIn("tara_sablonlar", dict(MENU))
        self.assertIn("/tara_sablonlar", HELP_TEXT)


if __name__ == "__main__":
    unittest.main()
