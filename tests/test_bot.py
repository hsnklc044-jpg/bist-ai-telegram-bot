import unittest

from bot.common import TELEGRAM_LIMIT, split_message


class SplitMessageTest(unittest.TestCase):
    def test_short_text_untouched(self):
        self.assertEqual(split_message("merhaba"), ["merhaba"])

    def test_long_text_split_on_lines(self):
        text = "\n".join(f"satır {i}" for i in range(2000))
        parts = split_message(text)

        self.assertGreater(len(parts), 1)
        self.assertTrue(all(len(p) <= TELEGRAM_LIMIT for p in parts))
        self.assertEqual("".join(parts), text)

    def test_single_huge_line(self):
        parts = split_message("x" * (TELEGRAM_LIMIT * 2 + 5))

        self.assertTrue(all(len(p) <= TELEGRAM_LIMIT for p in parts))
        self.assertEqual(sum(map(len, parts)), TELEGRAM_LIMIT * 2 + 5)


class HandlerRegistrationTest(unittest.TestCase):
    def test_all_commands_restricted_to_chat(self):
        from telegram.ext import ApplicationBuilder

        from bot.handlers import COMMANDS, register_handlers

        app = ApplicationBuilder().token("123:ABC").build()
        register_handlers(app, chat_id=777)

        handlers = [h for group in app.handlers.values() for h in group]
        commands = {c for h in handlers for c in h.commands}

        self.assertEqual(commands, {name for name, _ in COMMANDS})

        for handler in handlers:
            self.assertEqual(handler.filters.chat_ids, frozenset({777}))
