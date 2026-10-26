import asyncio
import re
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pandas as pd

from core.market import store
from core.market.universe import BENCHMARK
from core.reports import overview
from core.reports.daily import DISCLAIMER
from tests.helpers import offline_market

# Words that would read as a trading call. The disclaimer itself ("Bot AL/SAT
# önerisi vermez") is removed before the check.
TRADE_CALL = re.compile(r"\b(BUY|SELL|HOLD|ACCUMULATE|REDUCE|AL|SAT|AI DECISION)\b")

SYMBOLS = ["THYAO.IS", "EREGL.IS", "GARAN.IS"]


def _calls(text: str) -> list[str]:
    return TRADE_CALL.findall(text.replace(DISCLAIMER, ""))


class PrivateFiles:
    """Point every personal record at an empty temporary folder."""

    def __enter__(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = self.root = Path(self._tmp.name)
        self.paths = {
            "ledger": root / "ledger.csv",
            "alerts": root / "alerts_log.csv",
            "signals": root / "signal_log.csv",
        }
        self._patches = [
            mock.patch.object(overview, "LEDGER_FILE", self.paths["ledger"]),
            mock.patch.object(overview, "ALERTS_LOG_FILE", self.paths["alerts"]),
            mock.patch("core.signals_log.SIGNAL_LOG_FILE", self.paths["signals"]),
            mock.patch("core.reports.forward.SIGNAL_LOG_FILE", self.paths["signals"]),
            mock.patch("core.reports.forward.EQUITY_LOG_FILE", self.root / "equity_log.csv"),
            mock.patch("core.reports.health.SIGNAL_LOG_FILE", self.paths["signals"]),
            mock.patch("core.reports.health.EQUITY_LOG_FILE", self.root / "equity_log.csv"),
            mock.patch.dict("os.environ", {"BACKUP_DIR": str(root / "backups")}),
        ]
        for p in self._patches:
            p.start()
        return self

    def __exit__(self, *exc):
        for p in self._patches:
            p.stop()
        self._tmp.cleanup()


class OverviewTest(unittest.TestCase):
    def test_sections_and_no_trade_calls(self):
        with offline_market(), PrivateFiles():
            store.update([BENCHMARK, *SYMBOLS])
            text = overview.build_overview(SYMBOLS).text

        self.assertIn("QuantBIST özet", text)
        self.assertIn("XU100", text)
        self.assertIn("Sanal hesap", text)
        self.assertIn("Açık risk uyarısı yok", text)
        self.assertEqual(_calls(text), [])

    def test_read_only(self):
        with offline_market(), PrivateFiles() as files:
            overview.build_overview()

            self.assertFalse(any(p.exists() for p in files.paths.values()))

    def test_without_prices(self):
        with offline_market(), PrivateFiles(), mock.patch.object(
            overview, "adjusted_bars", return_value=pd.DataFrame()
        ):
            text = overview.build_overview().text

        self.assertIn("fiyat verisi yok", text)


class NoTradeCallsTest(unittest.TestCase):
    """The bot says it gives no buy/sell advice; none of its outputs may contradict that."""

    def _run(self, handler, args=()):
        sent: list[str] = []

        async def reply_text(text, **kwargs):
            sent.append(text)

        message = SimpleNamespace(reply_text=reply_text)
        update = SimpleNamespace(message=message, effective_message=message)
        asyncio.run(handler(update, SimpleNamespace(args=list(args))))

        return "\n".join(sent)

    def test_bot_commands(self):
        from bot.analysis import analyze, top
        from bot.reports import performance, status, summary
        from bot.start import start

        with offline_market(), PrivateFiles():
            store.update([BENCHMARK, *SYMBOLS])
            outputs = {
                "/help": self._run(start),
                "/summary": self._run(summary),
                "/top": self._run(top),
                "/analyze": self._run(analyze, ["THYAO"]),
                "/performans": self._run(performance),
                "/durum": self._run(status),
            }

        for command, text in outputs.items():
            with self.subTest(command=command):
                self.assertTrue(text)
                self.assertEqual(_calls(text), [])

    def test_web_panel(self):
        from fastapi.testclient import TestClient

        from core.web.app import app

        with offline_market(), PrivateFiles():
            store.update([BENCHMARK, *SYMBOLS])
            page = TestClient(app).get("/dashboard")

        self.assertEqual(page.status_code, 200)
        self.assertEqual(_calls(page.text), [])


if __name__ == "__main__":
    unittest.main()
