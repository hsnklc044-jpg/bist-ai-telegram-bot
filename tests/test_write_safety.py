"""Writes that can collide (daily report vs Telegram commands) and Telegram send failures."""

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from core.ledger.commands import parse_paper, parse_trade
from core.ledger.paper import load_orders
from core.ledger.service import paper_action, record_trade
from core.market.calendar import ISTANBUL
from core.reports import daily, runs


class LockedWritesTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        d = Path(tmp.name)
        self.orders, self.ledger = d / "orders.csv", d / "ledger.csv"

    def test_paper_order_waits_for_a_running_report(self):
        with runs.report_lock():
            text = paper_action(parse_paper(["al", "THYAO", "10"]), self.orders, self.ledger,
                                now=datetime(2026, 10, 26, 15, tzinfo=ISTANBUL))
        self.assertIn("kaydedilmedi", text)
        self.assertEqual(load_orders(self.orders), [])  # nothing half-written

        # the order list is read-only and still answers
        with runs.report_lock():
            self.assertIn("Bekleyen sanal emir yok", paper_action(parse_paper([]), self.orders, self.ledger))

    def test_trade_waits_for_a_running_report(self):
        with runs.report_lock():
            text = record_trade(parse_trade(["al", "THYAO", "10", "100", "01.10.2026"]), self.ledger)
        self.assertIn("kaydedilmedi", text)
        self.assertFalse(self.ledger.exists())

    def test_lock_is_released_after_a_command(self):
        record_trade(parse_trade(["al", "THYAO", "10", "100", "01.10.2026"]), self.ledger)
        self.assertFalse(runs.LOCK_FILE.exists())


class SendRetryTest(unittest.TestCase):
    def _post(self, outcomes):
        calls = []

        def post(url, json=None, timeout=None):
            calls.append(json["text"])
            outcome = outcomes.pop(0)
            if isinstance(outcome, Exception):
                raise outcome
            return SimpleNamespace(status_code=outcome, raise_for_status=lambda: None)

        return post, calls

    def test_network_error_and_5xx_are_retried(self):
        post, calls = self._post([ConnectionError("ağ yok"), 502, 200])
        pauses = []
        daily.send_telegram("rapor", "T", 1, post=post, sleep=pauses.append)
        self.assertEqual(len(calls), 3)
        self.assertEqual(pauses, [5, 20])

    def test_gives_up_after_three_attempts(self):
        post, calls = self._post([ConnectionError("x")] * 3)
        with self.assertRaises(ConnectionError):
            daily.send_telegram("rapor", "T", 1, post=post, sleep=lambda s: None)
        self.assertEqual(len(calls), 3)

    def test_wrong_token_is_not_retried(self):
        def post(url, json=None, timeout=None):
            def fail():
                raise ValueError("401 Unauthorized")
            return SimpleNamespace(status_code=401, raise_for_status=fail)

        with self.assertRaises(ValueError):
            daily.send_telegram("rapor", "T", 1, post=post, sleep=lambda s: self.fail("retried"))

    def test_a_sent_part_is_not_sent_again(self):
        long_text = "\n".join(f"satır {i}" for i in range(2000))
        parts = daily.split_text(long_text)
        post, calls = self._post([200, ConnectionError("x"), *[200] * len(parts)])
        daily.send_telegram(long_text, "T", 1, post=post, sleep=lambda s: None)
        self.assertEqual(calls.count(parts[0]), 1)
        self.assertEqual(len(calls), len(parts) + 1)


if __name__ == "__main__":
    unittest.main()
