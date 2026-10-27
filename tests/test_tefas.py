"""TEFAS money market fund prices for the cash return (Aşama 3 prerequisite). No network in tests."""

import tempfile
import unittest
from datetime import date
from pathlib import Path

import pandas as pd

from core.backtest import tefas
from core.backtest.cash import load_fund_prices


def ms(day):  # TEFAS gives dates as epoch milliseconds in a string
    return str(int(pd.Timestamp(day).timestamp() * 1000))


def row(day, code, name, price, size):
    return {"TARIH": ms(day), "FONKODU": code, "FONUNVAN": name, "FIYAT": price, "PORTFOYBUYUKLUK": size}


class FakeTefas:
    def __init__(self, rows):
        self.rows, self.calls = rows, []

    def __call__(self, url, data, headers, timeout):
        self.calls.append(data)
        lo = pd.Timestamp(pd.to_datetime(data["bastarih"], format="%d.%m.%Y"))
        hi = pd.Timestamp(pd.to_datetime(data["bittarih"], format="%d.%m.%Y"))
        out = [r for r in self.rows
               if lo <= pd.to_datetime(int(r["TARIH"]), unit="ms") <= hi
               and (not data["fonkod"] or r["FONKODU"] == data["fonkod"])]
        return type("R", (), {"status_code": 200, "json": lambda self: {"data": out}, "raise_for_status": lambda self: None})()


ROWS = [
    row("2023-07-31", "AAA", "A PORTFÖY PARA PİYASASI (TL) FONU", 1.10, 5e9),
    row("2023-07-31", "BBB", "B PORTFÖY PARA PİYASASI FONU", 2.00, 9e9),
    row("2023-07-31", "HHH", "H PORTFÖY HİSSE SENEDİ FONU", 3.00, 20e9),
    *[row(d, "BBB", "B PORTFÖY PARA PİYASASI FONU", 2.0 * (1.001 ** i), 9e9)
      for i, d in enumerate(pd.bdate_range("2023-07-31", "2023-10-31"))],
]


class SelectionTest(unittest.TestCase):
    def test_largest_money_market_fund_on_the_selection_day(self):
        fake = FakeTefas(ROWS)
        code, name = tefas.select_fund(date(2023, 7, 31), post=fake)
        self.assertEqual(code, "BBB")  # the equity fund is bigger but not a money market fund
        self.assertIn("PARA PİYASASI", name)


class HistoryTest(unittest.TestCase):
    def test_prices_in_chunks_and_written_with_a_source(self):
        fake = FakeTefas(ROWS)
        prices = tefas.fund_history("BBB", date(2023, 7, 31), date(2023, 10, 31), post=fake)
        self.assertEqual(len(prices), len(pd.bdate_range("2023-07-31", "2023-10-31")))
        self.assertGreater(len(fake.calls), 1)  # long ranges are asked in pieces
        self.assertTrue(prices.index.is_monotonic_increasing)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ppf.csv"
            tefas.write_prices(prices, "BBB", path)
            loaded = load_fund_prices(path)
        self.assertAlmostEqual(loaded.prices.iloc[-1], prices.iloc[-1])

    def test_missing_days_inside_the_period_are_reported(self):
        gap = [r for r in ROWS if r["TARIH"] != ms("2023-09-15")]
        prices = tefas.fund_history("BBB", date(2023, 7, 31), date(2023, 10, 31), post=FakeTefas(gap))
        self.assertEqual(tefas.missing_business_days(prices, date(2023, 8, 1), date(2023, 10, 31)),
                         [date(2023, 9, 15)])


if __name__ == "__main__":
    unittest.main()
