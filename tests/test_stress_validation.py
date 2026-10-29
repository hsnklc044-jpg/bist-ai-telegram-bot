"""
Bağımsız doğrulama M12 (ORTA, docs/validation/M12.md): the stress windows counted data rows, not
sessions — with a 5-session gap in XU100 the "worst 1 session" spanned 19.01 → 29.01. A window over
missing data is now skipped (holidays are allowed: exactly by the holiday file where it covers the
year, up to a Bayram's length before). Holdings without a price were dropped silently; now named.
"""

import unittest
from unittest import mock

import pandas as pd

from core.reports import stress


class GapTest(unittest.TestCase):
    def test_a_window_over_missing_sessions_is_skipped(self):
        days = pd.bdate_range("2026-01-05", periods=40)
        close = pd.Series(100.0, index=days)
        close.iloc[20:] = 95.0  # a real −5% day
        gap = close.drop(days[30:37])  # 7 sessions missing in the data
        gap.loc[days[37]:] = 80.0  # looks like −15,8% in "one session"
        (one,) = stress.worst_windows(gap, lengths=(1,))
        self.assertAlmostEqual(one.market, -0.05)
        self.assertEqual(one.end, days[20])

    def test_an_old_bayram_is_allowed(self):
        days = pd.bdate_range("2023-06-20", periods=20)
        close = pd.Series(100.0, index=days).drop(days[6:10])  # 4 weekdays of Kurban Bayramı
        close.loc[days[10]:] = 92.0
        (one,) = stress.worst_windows(close, lengths=(1,))
        self.assertAlmostEqual(one.market, -0.08)


class UnpricedTest(unittest.TestCase):
    def test_holding_without_price_is_named(self):
        from types import SimpleNamespace

        holdings = [SimpleNamespace(position=SimpleNamespace(symbol="AAA.IS"), value=1000.0),
                    SimpleNamespace(position=SimpleNamespace(symbol="BBB.IS"), value=float("nan"))]
        xu = pd.DataFrame({"close": [100.0] * 30 + [90.0] * 5}, index=pd.bdate_range("2026-01-05", periods=35))
        with mock.patch("core.ledger.load_ledger", return_value=[]), \
                mock.patch("core.reports.daily.value_holdings", return_value=(holdings, 1000.0)), \
                mock.patch("core.reports.daily.adjusted_bars", return_value=xu):
            text = stress.stress_text("real")
        self.assertIn("BBB", text)
        self.assertIn("Fiyatı yok", text)


if __name__ == "__main__":
    unittest.main()
