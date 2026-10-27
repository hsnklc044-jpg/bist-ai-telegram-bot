import tempfile
import unittest
from datetime import date
from pathlib import Path

from core.config.trading import PAPER_INITIAL_CAPITAL
from core.ledger import (
    Entry,
    LedgerError,
    append_entry,
    cash_balance,
    load_ledger,
    open_positions,
    replay,
)

D = date.fromisoformat


def e(day, side, qty, price, fee=0.0, symbol="THYAO", account="real"):
    return Entry(D(day), account, symbol, side, qty, price, fee).validate()


class FifoTest(unittest.TestCase):
    def test_average_cost_includes_fees(self):
        pos = replay([e("2026-01-05", "buy", 100, 10, fee=5)])[("real", "THYAO.IS")]
        self.assertAlmostEqual(pos.average_cost, 10.05)
        self.assertEqual(pos.quantity, 100)

    def test_partial_sell_is_fifo(self):
        entries = [
            e("2026-01-05", "buy", 100, 10),
            e("2026-01-06", "buy", 100, 20),
            e("2026-01-07", "sell", 150, 30, fee=3),
        ]
        pos = replay(entries)[("real", "THYAO.IS")]
        # sold 100 @ cost 10 and 50 @ cost 20 for 150 * 30 - 3
        self.assertAlmostEqual(pos.realized, 4500 - 3 - (1000 + 1000))
        self.assertEqual(pos.quantity, 50)
        self.assertAlmostEqual(pos.average_cost, 20)
        self.assertEqual(pos.opened, D("2026-01-06"))

    def test_oversell_rejected(self):
        with self.assertRaises(LedgerError):
            replay([e("2026-01-05", "buy", 10, 10), e("2026-01-06", "sell", 11, 10)])

    def test_sell_before_buy_rejected_even_if_listed_first(self):
        with self.assertRaises(LedgerError):
            replay([e("2026-01-07", "buy", 10, 10), e("2026-01-06", "sell", 10, 10)])

    def test_bonus_splits_lots_without_changing_cost(self):
        entries = [e("2026-01-05", "buy", 100, 10), e("2026-02-01", "bonus", 900, 0)]
        pos = replay(entries)[("real", "THYAO.IS")]
        self.assertAlmostEqual(pos.quantity, 1000)
        self.assertAlmostEqual(pos.cost, 1000)
        self.assertAlmostEqual(pos.average_cost, 1.0)

    def test_rights_add_a_lot_at_subscription_price(self):
        entries = [e("2026-01-05", "buy", 100, 5), e("2026-02-01", "rights", 100, 1)]
        pos = replay(entries)[("real", "THYAO.IS")]
        self.assertEqual(pos.quantity, 200)
        self.assertAlmostEqual(pos.average_cost, 3.0)

    def test_accounts_are_separate(self):
        entries = [e("2026-01-05", "buy", 10, 10), e("2026-01-05", "buy", 20, 10, account="paper")]
        self.assertEqual([p.quantity for p in open_positions(entries, "real")], [10])
        self.assertEqual([p.quantity for p in open_positions(entries, "paper")], [20])

    def test_as_of(self):
        entries = [e("2026-01-05", "buy", 10, 10), e("2026-01-09", "sell", 10, 12)]
        self.assertEqual(len(open_positions(entries, as_of=D("2026-01-06"))), 1)
        self.assertEqual(len(open_positions(entries)), 0)

    def test_paper_cash(self):
        entries = [
            e("2026-01-05", "buy", 100, 10, fee=1, account="paper"),
            e("2026-01-06", "sell", 100, 12, fee=1, account="paper"),
        ]
        self.assertAlmostEqual(cash_balance(entries, "paper"), PAPER_INITIAL_CAPITAL - 1001 + 1199)


class ValidationTest(unittest.TestCase):
    def test_bad_values(self):
        for bad in (
            Entry(D("2026-01-05"), "demo", "THYAO", "buy", 1, 1),
            Entry(D("2026-01-05"), "real", "THYAO", "short", 1, 1),
            Entry(D("2026-01-05"), "real", "THYAO", "buy", 0, 1),
            Entry(D("2026-01-05"), "real", "THYAO", "buy", 1, 0),
            Entry(D("2026-01-05"), "real", "THYAO", "bonus", 1, 5),
            Entry(D("2026-01-05"), "real", "THYAO", "buy", 1, 1, fee=-1),
            Entry(D("2026-01-05"), "real", "TH*", "buy", 1, 1),
        ):
            with self.subTest(entry=bad), self.assertRaises((LedgerError, ValueError)):
                bad.validate()

    def test_future_date_rejected(self):
        with self.assertRaises(LedgerError):
            Entry(D("2026-02-01"), "real", "THYAO", "buy", 1, 1).validate(today=D("2026-01-31"))


class FileTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "ledger.csv"

    def tearDown(self):
        self.tmp.cleanup()

    def test_round_trip_and_ids(self):
        a = append_entry(Entry(D("2026-01-05"), "real", "thyao", "buy", 100, 285.5, 28.55), self.path)
        b = append_entry(Entry(D("2026-01-06"), "real", "THYAO.IS", "sell", 40, 290.25, 11.61), self.path)
        self.assertEqual((a.id, b.id), (1, 2))
        loaded = load_ledger(self.path)
        self.assertEqual([x.symbol for x in loaded], ["THYAO.IS", "THYAO.IS"])
        self.assertEqual(loaded[0].price, 285.5)
        self.assertEqual(open_positions(loaded)[0].quantity, 60)

    def test_oversell_not_written(self):
        append_entry(Entry(D("2026-01-05"), "real", "THYAO", "buy", 10, 10), self.path)
        with self.assertRaises(LedgerError):
            append_entry(Entry(D("2026-01-06"), "real", "THYAO", "sell", 11, 10), self.path)
        self.assertEqual(len(load_ledger(self.path)), 1)

    def test_paper_cash_limit(self):
        with self.assertRaises(LedgerError):
            append_entry(
                Entry(D("2026-01-05"), "paper", "THYAO", "buy", 1, PAPER_INITIAL_CAPITAL + 1), self.path
            )
        self.assertFalse(self.path.exists())

    def test_bad_row_stops_with_line_number(self):
        self.path.write_text(
            "id,date,account,symbol,side,quantity,price,fee,note\n"
            "1,2026-01-05,real,THYAO.IS,buy,10,10,0,\n"
            "2,2026-01-06,real,THYAO.IS,buy,abc,10,0,\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(LedgerError, "satır 3"):
            load_ledger(self.path)

    def test_missing_file_is_empty(self):
        self.assertEqual(load_ledger(self.path), [])


if __name__ == "__main__":
    unittest.main()


class DividendTest(unittest.TestCase):
    """Audit D13 (user decision 27.10.2026): a cash dividend is income, not a gain hidden in the price."""

    def test_dividend_is_cash_in_and_realized_without_touching_the_lots(self):
        entries = [e("2026-01-05", "buy", 100, 50, fee=5), e("2026-05-20", "dividend", 100, 3.25)]
        pos = replay(entries)[("real", "THYAO.IS")]
        self.assertEqual(pos.quantity, 100)
        self.assertAlmostEqual(pos.average_cost, 50.05)  # the cost basis does not change
        self.assertAlmostEqual(pos.realized, 325.0)  # 100 × 3,25
        self.assertAlmostEqual(entries[1].amount, 325.0)

    def test_paper_cash_receives_it(self):
        entries = [e("2026-01-05", "buy", 10, 100, account="paper"), e("2026-05-20", "dividend", 10, 2, account="paper")]
        self.assertAlmostEqual(cash_balance(entries, "paper"), PAPER_INITIAL_CAPITAL - 1000 + 20)

    def test_more_shares_than_held_is_refused(self):
        with self.assertRaises(LedgerError):
            replay([e("2026-01-05", "buy", 10, 100), e("2026-05-20", "dividend", 11, 2)])
        with self.assertRaises(LedgerError):
            replay([e("2026-05-20", "dividend", 1, 2)])

    def test_amount_must_be_positive_and_no_fee(self):
        for price, fee in ((0, 0), (2, 1)):
            with self.subTest(price=price, fee=fee), self.assertRaises(LedgerError):
                Entry(D("2026-05-20"), "real", "THYAO", "dividend", 10, price, fee).validate()
