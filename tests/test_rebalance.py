"""
Rebalancing helper (road plan part 2): the distance of each holding from the user's own target
weight and the fewest whole-lot trades that bring it back inside a band. Arithmetic, no order,
no advice.
"""

import unittest
from datetime import date

from core.ledger.book import Entry
from core.reports import rebalance as R


class ParseTest(unittest.TestCase):
    def test_targets_band_and_account(self):
        got = R.parse(["THYAO=30", "asels=%20", "bant=3", "sanal"])
        self.assertEqual(got.targets, {"THYAO.IS": 0.30, "ASELS.IS": 0.20})
        self.assertEqual((got.band, got.account), (0.03, "paper"))

    def test_errors(self):
        for words in ([], ["THYAO"], ["THYAO=abc"], ["THYAO=120"], ["THYAO=60", "ASELS=50"], ["THYAO=30", "bant=60"],
                      ["A=30"]):
            with self.assertRaises(R.RebalanceError, msg=words):
                R.parse(words)


class PlanTest(unittest.TestCase):
    def test_fewest_trades_inside_the_band(self):
        # value 10.000: A 6.000 (60%), B 3.000 (30%), C 1.000 (10%); prices A 100, B 50, C 10
        holdings = {"A.IS": (60, 100.0), "B.IS": (60, 50.0), "C.IS": (100, 10.0)}
        plan = R.plan(holdings, {"A.IS": 0.40, "B.IS": 0.32}, total=10_000, band=0.05)
        rows = {r.symbol: r for r in plan.rows}
        self.assertEqual(rows["A.IS"].lots, -20)    # 60% -> 40%: sell 20 x 100
        self.assertEqual(rows["B.IS"].lots, 0)      # 30% vs 32%: inside the 5-point band
        self.assertIsNone(rows["C.IS"].target)      # no target: left as it is
        self.assertEqual(rows["C.IS"].lots, 0)
        self.assertAlmostEqual(plan.cash_change, 2_000)

    def test_a_new_stock_and_whole_lots(self):
        plan = R.plan({"A.IS": (100, 100.0)}, {"A.IS": 0.5, "B.IS": 0.5}, total=10_000, band=0.0,
                      prices={"B.IS": 33.0})
        rows = {r.symbol: r for r in plan.rows}
        self.assertEqual(rows["A.IS"].lots, -50)
        self.assertEqual(rows["B.IS"].lots, 151)  # 5.000 / 33 = 151,5 -> 151 whole shares

    def test_no_price_is_said(self):
        plan = R.plan({"A.IS": (10, 100.0)}, {"A.IS": 0.5, "B.IS": 0.5}, total=1000, band=0.0, prices={})
        self.assertIn("B.IS", plan.unpriced)

    def test_sell_never_exceeds_holding(self):
        plan = R.plan({"A.IS": (10, 100.0)}, {"A.IS": 0.0}, total=1000, band=0.0)
        self.assertEqual(plan.rows[0].lots, -10)


class TextTest(unittest.TestCase):
    def test_wording(self):
        entries = [Entry(date(2026, 9, 1), "real", "THYAO.IS", "buy", 60, 100.0, 0.0),
                   Entry(date(2026, 9, 1), "real", "GARAN.IS", "buy", 100, 10.0, 0.0)]
        import pandas as pd

        prices = {"THYAO.IS": 100.0, "GARAN.IS": 10.0, "ASELS.IS": 50.0}
        bars = lambda s: pd.DataFrame({"close": [prices[s]]}, index=[pd.Timestamp("2026-10-30")])  # noqa: E731
        text = R.text(["THYAO=50", "ASELS=30"], entries=entries, bars=bars)
        self.assertIn("öneri değil", text)
        self.assertIn("emir verilmez", text)
        self.assertIn("THYAO: %85,7 → hedef %50,0", text)
        self.assertIn("sat 25", text)
        self.assertIn("ASELS: %0,0 → hedef %30,0", text)
        self.assertIn("GARAN: %14,3 (hedef yok, dokunulmadı)", text)
        self.assertIn("al 42", text)

    def test_usage(self):
        self.assertIn("Kullanım", R.text([], entries=[], bars=None))

    def test_command_registered(self):
        from bot import handlers

        self.assertIn("denge", [name for name, _ in handlers.COMMANDS])


if __name__ == "__main__":
    unittest.main()
