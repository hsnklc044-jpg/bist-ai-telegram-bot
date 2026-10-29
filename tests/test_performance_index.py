"""
Bağımsız doğrulama M14 (YÜKSEK, docs/validation/M14.md): on a buy day the real account's return
divided the new money's gain by the old value only (+9,9% for a +5% day; +293% with a large buy).
Now money put in counts from the start of the period and money taken out at its end (Modified
Dietz with weights 1 and 0), so a day's return is the shares' own move. Hand-computed cases.
"""

import unittest
from datetime import date

import pandas as pd

from core.ledger.book import Entry
from core.reports.daily import performance_index


def equity(*values, start="2026-10-26"):
    return pd.Series(values, index=pd.bdate_range(start, periods=len(values)), dtype=float)


class BuyDayTest(unittest.TestCase):
    def test_validators_example(self):
        # 10.000 TL held; 10.000 TL more bought at yesterday's close; the stock closes +5%
        entries = [Entry(date(2026, 10, 27), "real", "AAA.IS", "buy", 100, 100.0)]
        growth = performance_index(equity(10_000.0, 21_000.0), entries, "real")
        self.assertAlmostEqual(growth.iloc[-1], 1.05)

    def test_large_buy_never_explodes(self):
        entries = [Entry(date(2026, 10, 27), "real", "AAA.IS", "buy", 1000, 100.0)]
        up = performance_index(equity(1_000.0, 1_030.0 + 103_000.0), entries, "real")
        down = performance_index(equity(1_000.0, 970.0 + 97_000.0), entries, "real")
        self.assertAlmostEqual(up.iloc[-1], 1.03)
        self.assertAlmostEqual(down.iloc[-1], 0.97)

    def test_sale_and_dividend(self):
        # 20.000 TL held, half sold for 10.500 (+5%), the rest closes at 10.500: the day is +5%
        sale = [Entry(date(2026, 10, 27), "real", "AAA.IS", "sell", 100, 105.0)]
        self.assertAlmostEqual(performance_index(equity(20_000.0, 10_500.0), sale, "real").iloc[-1], 1.05)
        # a flat day with a 200 TL dividend on 10.000 TL: +2%
        dividend = [Entry(date(2026, 10, 27), "real", "AAA.IS", "dividend", 100, 2.0)]
        self.assertAlmostEqual(performance_index(equity(10_000.0, 10_000.0), dividend, "real").iloc[-1], 1.02)

    def test_paper_account_unchanged(self):
        entries = [Entry(date(2026, 10, 27), "paper", "AAA.IS", "buy", 100, 100.0)]
        growth = performance_index(equity(100_000.0, 101_000.0), entries, "paper")
        self.assertAlmostEqual(growth.iloc[-1], 1.01)


if __name__ == "__main__":
    unittest.main()
