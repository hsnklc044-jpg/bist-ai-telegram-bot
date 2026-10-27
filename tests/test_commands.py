import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

from core.alerts import evaluate_account, update_alert_log
from core.ledger import LedgerError, load_ledger
from core.ledger.commands import parse_number, parse_paper, parse_trade
from core.ledger.service import alerts_text, paper_action, portfolio_text, record_trade
from core.market import store
from core.market.calendar import ISTANBUL
from tests.helpers import offline_market


class ParseTest(unittest.TestCase):
    def test_numbers(self):
        self.assertEqual(parse_number("285,50"), 285.5)
        self.assertEqual(parse_number("1.234,5"), 1234.5)
        self.assertEqual(parse_number("1234.5"), 1234.5)
        self.assertEqual(parse_number("100"), 100)
        with self.assertRaises(LedgerError):
            parse_number("yüz")

    def test_trade(self):
        c = parse_trade(["al", "thyao", "100", "285,50"])
        self.assertEqual((c.side, c.symbol, c.quantity, c.price, c.fee, c.day), ("buy", "thyao", 100, 285.5, None, None))
        c = parse_trade(["sat", "THYAO", "40", "290,25", "11,6", "22.10.2026"])
        self.assertEqual((c.side, c.fee, c.day), ("sell", 11.6, date(2026, 10, 22)))
        c = parse_trade(["bedelsiz", "CCOLA", "900"])
        self.assertEqual((c.side, c.price, c.fee), ("bonus", 0.0, 0.0))
        c = parse_trade(["bedelli", "KONTR", "100"])
        self.assertEqual((c.side, c.price), ("rights", 1.0))
        c = parse_trade(["temettü", "TUPRS", "100", "3,25", "20.05.2026"])
        self.assertEqual((c.side, c.quantity, c.price, c.fee, c.day), ("dividend", 100, 3.25, 0.0, date(2026, 5, 20)))
        with self.assertRaises(LedgerError):
            parse_trade(["temettu", "TUPRS", "100"])  # amount per share missing
        for bad in ([], ["al", "THYAO"], ["al", "THYAO", "10"], ["kirala", "THYAO", "1", "1"]):
            with self.subTest(args=bad), self.assertRaises(LedgerError):
                parse_trade(bad)

    def test_paper(self):
        self.assertEqual(parse_paper([]).action, "list")
        self.assertEqual(parse_paper(["iptal", "3"]).order_id, 3)
        c = parse_paper(["al", "THYAO", "100"])
        self.assertEqual((c.action, c.side, c.quantity), ("order", "buy", 100))
        for bad in (["iptal", "x"], ["bedelsiz", "THYAO", "1"], ["al", "THYAO"]):
            with self.subTest(args=bad), self.assertRaises(LedgerError):
                parse_paper(bad)


class ServiceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        self.ledger, self.orders, self.alerts = d / "l.csv", d / "o.csv", d / "a.csv"

    def tearDown(self):
        self.tmp.cleanup()

    def test_record_trade_default_commission(self):
        text = record_trade(parse_trade(["al", "THYAO", "100", "285,50"]), self.ledger, today=date(2026, 10, 23))
        self.assertIn("Deftere yazıldı (#1)", text)
        entry = load_ledger(self.ledger)[0]
        self.assertEqual((entry.account, entry.date), ("real", date(2026, 10, 23)))
        self.assertAlmostEqual(entry.fee, 28.55)

    def test_future_trade_refused(self):
        with self.assertRaises(LedgerError):
            record_trade(parse_trade(["al", "THYAO", "1", "1", "01.01.2027"]), self.ledger, today=date(2026, 10, 23))

    def test_paper_flow_and_portfolio(self):
        now = datetime(2026, 10, 20, 12, tzinfo=ISTANBUL)
        self.assertIn("#1", paper_action(parse_paper(["al", "AAA", "10"]), self.orders, self.ledger, now=now))
        self.assertIn("#1 al AAA", paper_action(parse_paper([]), self.orders, self.ledger))
        self.assertIn("iptal", paper_action(parse_paper(["iptal", "1"]), self.orders, self.ledger))
        self.assertIn("Bekleyen sanal emir yok", paper_action(parse_paper([]), self.orders, self.ledger))

        record_trade(parse_trade(["al", "AAA", "10", "50"]), self.ledger, today=date(2026, 10, 1))
        with offline_market():
            store.update(["AAA.IS"])
            text = portfolio_text(self.ledger)
        self.assertIn("Gerçek hesap", text)
        self.assertIn("AAA: 10 adet", text)
        self.assertIn("Sanal hesap", text)

    def test_alerts_text(self):
        self.assertIn("Açık risk uyarısı yok", alerts_text(self.alerts))
        import pandas as pd

        eq = pd.Series([100, 130, 100], index=pd.bdate_range("2026-01-05", periods=3), dtype=float)
        update_alert_log(evaluate_account("paper", eq), date(2026, 1, 7), self.alerts)
        self.assertIn("[yüksek] Sanal hesap", alerts_text(self.alerts))


if __name__ == "__main__":
    unittest.main()
