import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from core.ledger import Entry, append_entry
from core.portfolio import repository


class LedgerPortfolioTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ledger = Path(self.tmp.name) / "ledger.csv"

    def tearDown(self):
        self.tmp.cleanup()

    def test_empty_ledger_gives_none(self):
        self.assertIsNone(repository._ledger_portfolio(self.ledger, prices={}))

    def test_real_account_preferred(self):
        append_entry(Entry(date(2026, 10, 1), "paper", "THYAO", "buy", 10, 250), self.ledger)
        append_entry(Entry(date(2026, 10, 1), "real", "ASELS", "buy", 5, 300), self.ledger)
        df = repository._ledger_portfolio(self.ledger, prices={"ASELS.IS": 338.0, "THYAO.IS": 258.0})
        self.assertEqual(df["symbol"].tolist(), ["ASELS.IS"])
        self.assertAlmostEqual(df["value"].iloc[0], 5 * 338.0)
        self.assertIn("gerçek", df.attrs["source"])

    def test_load_portfolio_falls_back_to_sample(self):
        with mock.patch.object(repository, "_ledger_portfolio", return_value=None):
            df = repository.load_portfolio()
        self.assertIn("örnek", df.attrs["source"])
        self.assertFalse(df.empty)

    def test_load_portfolio_uses_ledger(self):
        append_entry(Entry(date(2026, 10, 1), "paper", "THYAO", "buy", 10, 250), self.ledger)
        df_ledger = repository._ledger_portfolio(self.ledger, prices={"THYAO.IS": 258.0})
        with mock.patch.object(repository, "_ledger_portfolio", return_value=df_ledger):
            df = repository.load_portfolio()
        self.assertEqual(df["symbol"].tolist(), ["THYAO.IS"])
        self.assertIn("sanal", df.attrs["source"])


if __name__ == "__main__":
    unittest.main()
