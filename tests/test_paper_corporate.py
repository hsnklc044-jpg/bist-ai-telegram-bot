"""
Bağımsız doğrulama M14 (YÜKSEK): the paper account had no way to record a bonus or rights issue,
so a 100% bonus issue showed as a 50% loss. /trade bedelsiz|bedelli|temettü ... sanal now writes to
the paper account; buys and sells there still go only through /paper orders (next open).
"""

import tempfile
import unittest
from datetime import date
from pathlib import Path

from core.ledger.book import Entry, append_entry, cash_balance, load_ledger, open_positions
from core.ledger.commands import LedgerError, parse_trade
from core.ledger.service import record_trade


class ParseTest(unittest.TestCase):
    def test_paper_word(self):
        self.assertEqual(parse_trade(["bedelsiz", "THYAO", "100", "sanal"]).account, "paper")
        self.assertEqual(parse_trade(["bedelli", "THYAO", "40", "1", "sanal"]).account, "paper")
        self.assertEqual(parse_trade(["temettü", "THYAO", "100", "3,25", "sanal"]).account, "paper")
        self.assertEqual(parse_trade(["bedelsiz", "THYAO", "100"]).account, "real")

    def test_buys_and_sales_stay_with_paper_orders(self):
        with self.assertRaises(LedgerError) as caught:
            parse_trade(["al", "THYAO", "10", "250", "sanal"])
        self.assertIn("/paper", str(caught.exception))


class RecordTest(unittest.TestCase):
    def test_bonus_on_paper_keeps_the_value(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.csv"
            append_entry(Entry(date(2026, 10, 20), "paper", "THYAO.IS", "buy", 10, 200.0, 2.0), path)
            text = record_trade(parse_trade(["bedelsiz", "THYAO", "10", "sanal"]), path, today=date(2026, 10, 28))
            entries = load_ledger(path)
        self.assertIn("Sanal hesap", text)
        (position,) = open_positions(entries, "paper")
        self.assertEqual(position.quantity, 20)  # 10 + 10 bonus: half the price, the same value
        self.assertEqual(open_positions(entries, "real"), [])
        self.assertAlmostEqual(cash_balance(entries, "paper"), 100_000.0 - 2002.0)


if __name__ == "__main__":
    unittest.main()
