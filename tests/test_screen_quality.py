"""
/tara Aşama 6: the command list Telegram shows (set at start-up; the same list is in HANDBOOK for
pasting into BotFather by hand), and CHARTER §9 for every /tara text and module: no order, no
broker, no token, no advice wording, the fixed last line.
"""

import re
import unittest
from pathlib import Path

from bot.handlers import COMMANDS, MENU

ROOT = Path(__file__).resolve().parents[1]
ADVICE = (r"\bal\b", r"\bsat\b", r"\balın\b", r"\bsatın\b", r"en iyi", r"öneri", r"tavsiye", r"fırsat",
          r"hedef fiyat", r"güçlü al", r"şampiyon")


class MenuTest(unittest.TestCase):
    def test_telegram_limits(self):
        self.assertLessEqual(len(MENU), 100)
        for name, description in MENU:
            with self.subTest(name):
                self.assertRegex(name, r"^[a-z0-9_]{1,32}$")
                self.assertTrue(1 <= len(description) <= 256)
        self.assertEqual(len({n for n, _ in MENU}), len(MENU))

    def test_every_command_is_in_the_menu(self):
        menu = dict(MENU)
        for name, _ in COMMANDS:
            if name.startswith("tara"):
                self.assertIn(name, menu)

    def test_handbook_has_the_botfather_list(self):
        text = (ROOT / "docs" / "HANDBOOK.md").read_text(encoding="utf-8")
        block = text.split("**BotFather listesi**", 1)[1].split("```", 2)[1]
        self.assertEqual(block.strip().splitlines(), [f"{n} - {d}" for n, d in MENU])


class CharterTest(unittest.TestCase):
    MODULES = sorted((ROOT / "core" / "screen").glob("*.py"))

    def test_no_order_broker_or_token_in_the_screen_modules(self):
        for path in self.MODULES:
            source = path.read_text(encoding="utf-8")
            code = source.split('"""', 2)[2] if source.startswith('"""') else source
            with self.subTest(path.name):
                for word in ("core.ledger", "PAPER_ORDERS_FILE", "LEDGER_FILE", "BOT_TOKEN", "bot_token", "requests.post",
                             "place_order", "broker"):
                    self.assertNotIn(word, code)

    def test_texts_carry_no_advice_and_end_with_the_fixed_line(self):
        from core.screen import command, subscriptions, templates, virtual

        texts = [templates.list_text(cards={}), command.help_text({}), command.fields_text(),
                 command.list_saved_text(ROOT / "nonexistent.csv"), virtual.command_text([], path=ROOT / "none.csv"),
                 subscriptions.list_text(ROOT / "none.csv")]
        message = subscriptions._message("x", "rsi<30", __import__("datetime").date(2026, 10, 28), ["A.IS"], ["B.IS"])
        texts.append(message)
        for text in texts:
            body = re.sub(r"(öneri|tavsiye)(si)? değil(dir)?", "", text.replace(command.DISCLAIMER, "").lower())
            for word in ADVICE:
                self.assertIsNone(re.search(word, body), (word, text[:80]))
        for text in (texts[0], texts[1], texts[3], texts[5], message):
            self.assertTrue(text.rstrip().endswith(command.DISCLAIMER), text[-80:])


if __name__ == "__main__":
    unittest.main()
