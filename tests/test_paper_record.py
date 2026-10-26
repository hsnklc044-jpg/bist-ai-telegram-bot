import csv
import math
import tempfile
import unittest
from dataclasses import replace
from datetime import date
from pathlib import Path

from core.config.trading import SLIPPAGE
from core.ledger import load_ledger
from core.ledger.commands import parse_paper
from core.ledger.paper import fill_pending, load_orders, order_snapshot, place_order, save_orders
from tests.helpers import make_ohlcv
from tests.test_paper import PRICES, at, bars

OLD_FIELDS = ("id", "created_at", "symbol", "side", "quantity", "status", "fill_date", "fill_price", "note")
OLD_FILE = (
    "id,created_at,symbol,side,quantity,status,fill_date,fill_price,note\n"
    "1,2026-10-20T10:00:00+03:00,THYAO.IS,buy,100,filled,2026-10-21,10.005,\n"
    "2,2026-10-22T12:00:00+03:00,EREGL.IS,buy,50,pending,,,\n"
)


class Files(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        d = Path(tmp.name)
        self.orders, self.ledger = d / "orders.csv", d / "ledger.csv"


class BackwardCompatibilityTest(Files):
    def test_old_file_loads_and_rewrites_without_losing_anything(self):
        self.orders.write_text(OLD_FILE, encoding="utf-8")
        orders = load_orders(self.orders)

        self.assertEqual([o.id for o in orders], [1, 2])
        self.assertEqual((orders[1].reason, orders[1].ref_close, orders[1].fill_log), ("", None, ""))

        save_orders(orders, self.orders)
        copy = self.orders.with_name("orders_before_v0.28.csv")
        self.assertEqual(copy.read_text(encoding="utf-8"), OLD_FILE)  # exact copy, once
        save_orders(orders, self.orders)
        self.assertEqual(copy.read_text(encoding="utf-8"), OLD_FILE)
        with open(self.orders, encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        old = list(csv.DictReader(OLD_FILE.splitlines()))
        for new_row, old_row in zip(rows, old, strict=True):
            self.assertEqual({k: new_row[k] for k in OLD_FIELDS}, old_row)

    def test_previous_version_can_read_the_new_file(self):
        # what v0.27 load_orders does: read the old columns by name
        place_order("THYAO", "buy", 10, now=at("2026-10-21T15:00:00"), orders_path=self.orders,
                    ledger_path=self.ledger, reason="test", snapshot={"ref_close": 10.0, "data_date": date(2026, 10, 21)})
        with open(self.orders, encoding="utf-8-sig", newline="") as fh:
            row = next(csv.DictReader(fh))
        self.assertEqual(list(row)[: len(OLD_FIELDS)], list(OLD_FIELDS))
        self.assertEqual((row["symbol"], row["status"], float(row["quantity"])), ("THYAO.IS", "pending", 10.0))


class RecordTest(Files):
    def test_reason_snapshot_and_size(self):
        frame = make_ohlcv(rows=150, seed=4)
        snap = order_snapshot("thyao", lambda s: frame, lambda s: frame, account_value=100_000)
        o = place_order("thyao", "buy", 100, now=at("2026-10-21T15:00:00"), orders_path=self.orders,
                        ledger_path=self.ledger, reason="  kırılım   sonrası ", snapshot=snap)

        self.assertEqual(o.reason, "kırılım sonrası")
        self.assertEqual(o.data_date, frame.index[-1].date())
        self.assertAlmostEqual(o.est_value, 100 * frame["close"].iloc[-1])
        self.assertAlmostEqual(o.account_share, o.est_value / 100_000)
        self.assertTrue(o.view and o.score is not None and o.atr_pct > 0)
        loaded = load_orders(self.orders)[0]  # survives a save/load round trip (10 significant digits)
        self.assertEqual((loaded.reason, loaded.view, loaded.data_date), (o.reason, o.view, o.data_date))
        for name in ("ref_close", "score", "est_value", "account_share", "atr_pct"):
            self.assertTrue(math.isclose(getattr(loaded, name), getattr(o, name), rel_tol=1e-9), name)

    def test_snapshot_never_blocks_the_order(self):
        def broken(symbol):
            raise OSError("db")

        snap = order_snapshot("thyao", broken, broken, None)
        o = place_order("thyao", "buy", 1, now=at("2026-10-21T15:00:00"), orders_path=self.orders,
                        ledger_path=self.ledger, snapshot=snap)
        self.assertIsNone(o.ref_close)

    def test_parse_reason(self):
        cmd = parse_paper(["al", "THYAO", "100", "trend", "devam", "ediyor"])
        self.assertEqual((cmd.side, cmd.quantity, cmd.reason), ("buy", 100, "trend devam ediyor"))
        self.assertEqual(parse_paper(["al", "THYAO", "100"]).reason, "")


class FillRecordTest(Files):
    def fill(self, prices=PRICES):
        return fill_pending(lambda s: prices, self.orders, self.ledger)

    def test_fill_costs_are_recorded(self):
        place_order("thyao", "buy", 100, now=at("2026-10-21T15:00:00"), orders_path=self.orders, ledger_path=self.ledger)
        o = self.fill()[0]
        self.assertEqual(o.fill_open, 10.2)
        self.assertAlmostEqual(o.fill_price, 10.2 * (1 + SLIPPAGE))
        self.assertAlmostEqual(o.fee, load_ledger(self.ledger)[0].fee, places=4)

    def test_locked_days_are_logged_once(self):
        locked = bars([
            ("2026-10-21", 10.0, 10.0, 10.0, 10.0),
            ("2026-10-22", 11.0, 11.0, 11.0, 11.0),  # limit-up, locked
        ])
        place_order("thyao", "buy", 10, now=at("2026-10-21T15:00:00"), orders_path=self.orders, ledger_path=self.ledger)

        self.assertEqual(self.fill(locked), [])
        self.assertEqual(self.fill(locked), [])
        o = load_orders(self.orders)[0]
        self.assertEqual((o.status, o.fill_log), ("pending", "22.10.2026 tavan kilidi, dolmadı"))

    def test_no_double_fill_after_an_interrupted_run(self):
        place_order("thyao", "buy", 100, now=at("2026-10-21T15:00:00"), orders_path=self.orders, ledger_path=self.ledger)
        before = load_orders(self.orders)
        self.fill()
        save_orders(before, self.orders)  # as if the run stopped before saving the orders

        changed = self.fill()
        self.assertEqual(len(load_ledger(self.ledger)), 1)
        self.assertEqual(changed[0].status, "filled")
        self.assertIn("ikinci kez yazılmadı", changed[0].fill_log)
        self.assertEqual(str(changed[0].fill_date), "2026-10-22")

    def test_round_trip_keeps_new_fields(self):
        place_order("thyao", "buy", 100, now=at("2026-10-21T15:00:00"), orders_path=self.orders, ledger_path=self.ledger)
        o = replace(load_orders(self.orders)[0], fill_log="a; b", atr_pct=0.031)
        save_orders([o], self.orders)
        self.assertEqual(load_orders(self.orders)[0], o)


class ServiceTextTest(Files):
    def test_order_message_shows_the_record(self):
        from unittest import mock

        from core.ledger import service

        frame = make_ohlcv(rows=150, seed=4)
        with mock.patch.object(service, "raw_bars", return_value=frame), \
                mock.patch.object(service, "adjusted_bars", return_value=frame):
            text = service.paper_action(parse_paper(["al", "THYAO", "10", "deneme"]), self.orders, self.ledger,
                                        now=at("2026-10-21T15:00:00"))

        self.assertIn("Kayda geçen", text)
        self.assertIn("Gerekçe: deneme", text)
        self.assertIn("sanal hesabın %", text)
        self.assertIn("tahmin gücü kanıtlanmadı", text)


if __name__ == "__main__":
    unittest.main()
