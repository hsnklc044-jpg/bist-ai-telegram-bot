import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import pandas as pd

from core.config.trading import COMMISSION, PAPER_INITIAL_CAPITAL, SLIPPAGE
from core.ledger import LedgerError, load_ledger, open_positions
from core.ledger.paper import cancel_order, fill_pending, load_orders, place_order
from core.market.calendar import ISTANBUL


def at(text):
    return datetime.fromisoformat(text).replace(tzinfo=ISTANBUL)


def bars(rows):
    """rows: (date, open, high, low, close)"""

    df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close"])
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")


PRICES = bars(
    [
        ("2026-10-21", 10.0, 10.5, 9.8, 10.0),
        ("2026-10-22", 10.2, 10.6, 10.0, 10.4),
        ("2026-10-23", 10.5, 10.9, 10.3, 10.8),
    ]
)


class PaperTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        self.orders, self.ledger = d / "orders.csv", d / "ledger.csv"

    def tearDown(self):
        self.tmp.cleanup()

    def place(self, *args, **kw):
        return place_order(*args, orders_path=self.orders, ledger_path=self.ledger, **kw)

    def fill(self, prices=PRICES):
        return fill_pending(lambda s: prices, self.orders, self.ledger)

    def test_fills_at_next_session_open_with_costs(self):
        self.place("thyao", "buy", 100, now=at("2026-10-21T15:00:00"))
        changed = self.fill()
        self.assertEqual(len(changed), 1)
        o = changed[0]
        self.assertEqual(str(o.fill_date), "2026-10-22")
        self.assertAlmostEqual(o.fill_price, 10.2 * (1 + SLIPPAGE))
        entry = load_ledger(self.ledger)[0]
        self.assertEqual(entry.account, "paper")
        # the ledger stores fees to 4 decimals (well below one kuruş)
        self.assertAlmostEqual(entry.fee, 10.2 * (1 + SLIPPAGE) * 100 * COMMISSION, places=4)

    def test_order_after_close_still_fills_next_day(self):
        self.place("THYAO", "buy", 10, now=at("2026-10-21T22:00:00"))
        self.assertEqual(str(self.fill()[0].fill_date), "2026-10-22")

    def test_order_before_the_open_fills_the_same_day(self):
        self.place("THYAO", "buy", 10, now=at("2026-10-22T01:01:00"))
        self.assertEqual(str(self.fill()[0].fill_date), "2026-10-22")

    def test_order_during_the_session_waits_for_the_next_open(self):
        self.place("THYAO", "buy", 10, now=at("2026-10-22T09:45:00"))
        self.assertEqual(str(self.fill()[0].fill_date), "2026-10-23")

    def test_no_fill_before_data_exists(self):
        self.place("THYAO", "buy", 10, now=at("2026-10-23T12:00:00"))
        self.assertEqual(self.fill(), [])
        self.assertEqual(load_orders(self.orders)[0].status, "pending")

    def test_filled_only_once(self):
        self.place("THYAO", "buy", 10, now=at("2026-10-21T12:00:00"))
        self.fill()
        self.assertEqual(self.fill(), [])
        self.assertEqual(len(load_ledger(self.ledger)), 1)

    def test_locked_limit_up_buy_waits(self):
        prices = bars(
            [
                ("2026-10-21", 10.0, 10.5, 9.8, 10.0),
                ("2026-10-22", 11.0, 11.0, 11.0, 11.0),  # locked limit-up
                ("2026-10-23", 11.5, 12.0, 11.2, 11.8),
            ]
        )
        self.place("THYAO", "buy", 10, now=at("2026-10-21T12:00:00"))
        self.assertEqual(str(self.fill(prices)[0].fill_date), "2026-10-23")

    def test_sell_needs_paper_position(self):
        with self.assertRaises(LedgerError):
            self.place("THYAO", "sell", 10, now=at("2026-10-21T12:00:00"))

    def test_buy_then_sell_round_trip(self):
        self.place("THYAO", "buy", 100, now=at("2026-10-21T12:00:00"))
        self.fill()
        self.place("THYAO", "sell", 100, now=at("2026-10-22T12:00:00"))
        self.fill()
        self.assertEqual(open_positions(load_ledger(self.ledger), "paper"), [])

    def test_too_expensive_buy_is_rejected_not_lost(self):
        self.place("THYAO", "buy", PAPER_INITIAL_CAPITAL, now=at("2026-10-21T12:00:00"))
        o = self.fill()[0]
        self.assertEqual(o.status, "rejected")
        self.assertIn("nakit", o.note)
        self.assertEqual(load_ledger(self.ledger), [])

    def test_cancel(self):
        o = self.place("THYAO", "buy", 10, now=at("2026-10-21T12:00:00"))
        cancel_order(o.id, self.orders)
        self.assertEqual(self.fill(), [])
        with self.assertRaises(LedgerError):
            cancel_order(o.id, self.orders)


if __name__ == "__main__":
    unittest.main()
