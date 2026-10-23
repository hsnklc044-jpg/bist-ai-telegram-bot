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


class AnalysisFormatTest(unittest.TestCase):
    def _result(self, signal):
        return {
            "symbol": "THYAO.IS", "price": 259.0, "signal": signal, "score": 20,
            "trend": "BEARISH", "rsi": 31.0968, "macd": -7.5677, "volume_ratio": 1.04,
            "volatility": 0.0304, "confidence": 25, "entry_price": 259.0,
            "stop_loss": 243.26, "target_1": 274.74, "target_2": 290.48,
            "ma20": 279.3522, "ma50": 290.0099,
        }

    def test_sell_signal_has_no_long_targets(self):
        from bot.analysis import _format_analysis

        text = _format_analysis(self._result("STRONG SELL"))

        self.assertNotIn("Target", text)
        self.assertNotIn("Stop Loss", text)
        self.assertIn("%3.04", text)

    def test_buy_signal_shows_levels(self):
        from bot.analysis import _format_analysis

        text = _format_analysis(self._result("BUY"))

        self.assertIn("Stop Loss : 243.26", text)
        self.assertIn("Target 2 : 290.48", text)
