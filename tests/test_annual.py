"""Yearly statement from the ledger (core/reports/annual.py): realized sales (FIFO, fees included),
net dividends and fees paid, for one account and calendar year. A statement, not tax advice."""

import unittest
from datetime import date

from core.ledger.book import Entry
from core.reports import annual


def e(d, side, symbol, qty, price, fee=0.0, account="real"):
    return Entry(date.fromisoformat(d), account, symbol, side, qty, price, fee)


LEDGER = [
    e("2025-03-01", "buy", "THYAO.IS", 100, 200, 2),        # unit cost 2.02... + fee
    e("2025-12-15", "sell", "THYAO.IS", 50, 250, 1),         # 2025: not in the 2026 statement
    e("2026-02-01", "buy", "THYAO.IS", 100, 300, 3),
    e("2026-05-10", "dividend", "THYAO.IS", 150, 4.25),       # net per share
    e("2026-06-20", "sell", "THYAO.IS", 100, 320, 3.2),       # FIFO: 50 @ 200.02 + 50 @ 300.03
    e("2026-07-01", "buy", "BIMAS.IS", 10, 500, 0.5, account="paper"),
]


class AnnualStatementTest(unittest.TestCase):
    def test_sales_dividends_and_fees_of_the_year(self):
        s = annual.statement(LEDGER, 2026, "real")
        self.assertEqual(len(s.sales), 1)
        sale = s.sales[0]
        self.assertEqual((sale.day, sale.symbol, sale.quantity), (date(2026, 6, 20), "THYAO.IS", 100))
        self.assertAlmostEqual(sale.proceeds, 100 * 320 - 3.2)
        self.assertAlmostEqual(sale.cost, 50 * (200 + 2 / 100) + 50 * (300 + 3 / 100))
        self.assertAlmostEqual(sale.result, sale.proceeds - sale.cost)
        self.assertEqual(len(s.dividends), 1)
        self.assertAlmostEqual(s.dividends[0].amount, 150 * 4.25)
        self.assertAlmostEqual(s.fees, 3 + 3.2)  # only 2026 fees of the real account
        self.assertAlmostEqual(s.total, sale.result + 150 * 4.25)

    def test_other_account_and_empty_year(self):
        self.assertAlmostEqual(annual.statement(LEDGER, 2026, "paper").fees, 0.5)
        empty = annual.statement(LEDGER, 2024, "real")
        self.assertEqual((empty.sales, empty.dividends, empty.fees), ([], [], 0.0))

    def test_text_is_labelled_and_turkish_formatted(self):
        text = annual.format_statement(annual.statement(LEDGER, 2026, "real"))
        self.assertIn("2026", text)
        self.assertIn("Gerçek hesap", text)
        self.assertIn("THYAO", text)
        self.assertIn("vergi danışmanlığı değildir", text)
        self.assertIn("satış 31.996,80 TL", text)  # 100 × 320 − 3,20 komisyon, Turkish format
        self.assertIn("yıl içinde satış yok", annual.format_statement(annual.statement(LEDGER, 2024, "real")))


class AnnualCommandTest(unittest.TestCase):
    def test_arguments(self):
        self.assertEqual(annual.parse_args([], today=date(2026, 10, 28)), (2026, "real"))
        self.assertEqual(annual.parse_args(["2025"], today=date(2026, 10, 28)), (2025, "real"))
        self.assertEqual(annual.parse_args(["2025", "sanal"], today=date(2026, 10, 28)), (2025, "paper"))
        self.assertEqual(annual.parse_args(["sanal"], today=date(2026, 10, 28)), (2026, "paper"))
        with self.assertRaises(ValueError):
            annual.parse_args(["geçen"], today=date(2026, 10, 28))


class LedgerFileTest(unittest.TestCase):
    def test_reads_the_ledger_file_and_explains_bad_words(self):
        import io
        import tempfile
        from contextlib import redirect_stdout
        from pathlib import Path
        from unittest import mock

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.csv"
            path.write_text("id,date,account,symbol,side,quantity,price,fee,note\n"
                            "1,2026-01-05,real,THYAO.IS,buy,10,100,1,\n"
                            "2,2026-03-05,real,THYAO.IS,sell,10,110,1,\n", encoding="utf-8")
            text = annual.annual_text(["2026"], date(2026, 10, 28), path=path)
        self.assertIn("sonuç 98,00 TL", text)  # 1.099 − 1.001
        self.assertIn("Kullanım: /yil", annual.annual_text(["dün"], date(2026, 10, 28)))
        out = io.StringIO()
        with mock.patch.object(annual, "annual_text", return_value="döküm"), redirect_stdout(out):
            self.assertEqual(annual.main(["2026"]), 0)
        self.assertIn("döküm", out.getvalue())


class YearCommandTest(unittest.TestCase):
    def test_bot_command_passes_the_words(self):
        from unittest import mock

        from bot.handlers import COMMANDS, MENU
        from bot.reports import yearly
        from bot.start import HELP_TEXT
        from tests.test_bot_handlers import run

        with mock.patch.object(annual, "annual_text", return_value="döküm") as made:
            self.assertEqual(run(yearly, ["2025", "sanal"]), "döküm")
        self.assertEqual(made.call_args.args[0], ["2025", "sanal"])
        self.assertIn("yil", dict(COMMANDS))
        self.assertIn("yil", dict(MENU))
        self.assertIn("/yil", HELP_TEXT)


if __name__ == "__main__":
    unittest.main()
