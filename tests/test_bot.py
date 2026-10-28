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

        from telegram.ext import CommandHandler

        handlers = [h for group in app.handlers.values() for h in group if isinstance(h, CommandHandler)]
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

        self.assertNotIn("ATR üstü", text)
        self.assertNotIn("STRONG", text)
        self.assertIn("Güçlü negatif", text)
        self.assertNotIn("Confidence", text)
        self.assertIn("%3.04", text)

    def test_buy_signal_shows_levels(self):
        from bot.analysis import _format_analysis

        text = _format_analysis(self._result("BUY"))

        self.assertIn("2 ATR altı : 243.26", text)
        self.assertIn("4 ATR üstü : 290.48", text)
        self.assertIn("tahmin gücü bulunmadı", text)


class SecondInstanceTest(unittest.TestCase):
    """Two bots with one token: Telegram refuses the second (Conflict). Seen on the user's PC, 27.10.2026."""

    def test_conflict_is_one_clear_line_without_a_traceback(self):
        import asyncio
        from types import SimpleNamespace

        from telegram.error import Conflict

        from bot import handlers

        error = Conflict("terminated by other getUpdates request; make sure that only one bot instance is running")
        from unittest import mock

        with mock.patch.object(handlers, "_conflict_reported", False), \
                self.assertLogs("bot.handlers", level="ERROR") as logs:
            asyncio.run(handlers.on_error(None, SimpleNamespace(error=error)))
            asyncio.run(handlers.on_error(None, SimpleNamespace(error=error)))  # repeats every few seconds
        self.assertEqual(len(logs.records), 1)  # said once, not on every retry
        record = logs.records[0]
        self.assertIn("aynı anda iki bot", record.getMessage())
        self.assertIsNone(record.exc_info)


class StartupNetworkTest(unittest.TestCase):
    """27.10 08:36 on the user's PC: one DNS failure (getaddrinfo) at start-up ended the bot
    ('Failed run number 0 of 0. Aborting.'). Start-up must retry a network error."""

    def test_start_up_retries_network_errors(self):
        from unittest import mock

        from bot import application

        app = mock.MagicMock()
        settings = mock.MagicMock(app_name="QuantBIST", version="test", chat_id=1)
        with mock.patch.object(application, "build_app", return_value=app), \
                mock.patch.object(application, "require_bot_settings", return_value=settings):
            application.main()
        retries = app.run_polling.call_args.kwargs.get("bootstrap_retries", 0)
        self.assertGreaterEqual(retries, 10)  # about 2 minutes of back-off before giving up

    def test_one_dns_failure_then_success_keeps_starting(self):
        """PC log 27.10 08:36: 'getaddrinfo failed' once, then the network was back. With our setting the
        library's retry loop must try again (with 0 retries it raised: 'Failed run number 0 of 0. Aborting.')."""

        import asyncio
        from unittest import mock

        from telegram.error import NetworkError
        from telegram.ext._utils.networkloop import network_retry_loop

        from bot.application import BOOTSTRAP_RETRIES

        calls = []

        async def get_me():
            calls.append(1)
            if len(calls) == 1:
                raise NetworkError("httpcore.ConnectError: [Errno 11001] getaddrinfo failed")

        async def start(retries):
            with mock.patch("asyncio.sleep", new=mock.AsyncMock()):  # no real back-off wait in tests
                await network_retry_loop(action_cb=get_me, description="Bootstrap Initialize Application",
                                         interval=1, max_retries=retries)

        asyncio.run(start(BOOTSTRAP_RETRIES))
        self.assertEqual(len(calls), 2)  # failed once, retried, started

        calls.clear()
        with self.assertRaises(NetworkError):  # the old default: the bot stopped at the first failure
            asyncio.run(start(0))

