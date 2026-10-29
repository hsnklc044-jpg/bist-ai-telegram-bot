"""
Bağımsız doğrulama M16 (YÜKSEK, docs/validation/M16.md): with the second source off, errors inside
BIST's ±10% limit were invisible — a one-day ×1,05 wrong candle was missed 91% of the time, a flat
broken candle (open = high = low = close, like BERA 27.06.2022) 94%, and the open was never checked
against the high–low range. These checks use only the candle itself, so they list (they do not
exclude): telling a real move from a wrong one needs a second source.
"""

import unittest

import numpy as np
import pandas as pd

from core.market.quality import check_symbol, format_report


def clean(rows=250, seed=4):
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.015, rows)))
    prev = np.r_[close[0], close[:-1]]
    open_ = prev * (1 + rng.normal(0, 0.003, rows))
    high = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, 0.006, rows)))
    low = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, 0.006, rows)))
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close,
                         "volume": rng.integers(1_000_000, 5_000_000, rows).astype(float)},
                        index=pd.bdate_range("2026-01-05", periods=rows))


class CandleIntegrityTest(unittest.TestCase):
    def test_clean_series_lists_nothing(self):
        q = check_symbol(clean(), "X.IS")
        self.assertEqual((q.bad_ohlc, q.flat_days, q.reversals), (0, [], []))

    def test_open_outside_the_range_is_bad(self):
        df = clean()
        df.iloc[50, df.columns.get_loc("open")] = df["high"].iloc[50] * 1.03
        self.assertEqual(check_symbol(df, "X.IS").bad_ohlc, 1)

    def test_flat_traded_candle_is_listed(self):
        df = clean()
        price = df["close"].iloc[49]
        df.iloc[50, :4] = price
        q = check_symbol(df, "X.IS")
        self.assertEqual(q.flat_days, [df.index[50].date().isoformat()])
        self.assertTrue(q.ok)  # listed, not excluded
        self.assertIn("düz mum", format_report([q]))

    def test_a_flat_day_without_trades_is_normal(self):
        df = clean()
        df.iloc[50, :4] = df["close"].iloc[49]
        df.iloc[50, df.columns.get_loc("volume")] = 0.0
        self.assertEqual(check_symbol(df, "X.IS").flat_days, [])

    def test_one_day_wrong_candle_undone_next_day_is_listed(self):
        df = clean()
        df.iloc[60, :4] *= 1.05  # the whole candle 5% off, next day back to normal
        q = check_symbol(df, "X.IS")
        self.assertEqual(q.reversals, [df.index[60].date().isoformat()])
        self.assertTrue(q.ok)
        self.assertIn("geri dönen", format_report([q]))

    def test_a_real_move_that_holds_is_not_listed(self):
        df = clean()
        df.iloc[60:, :4] *= 1.05  # a real +5% that stays
        self.assertEqual(check_symbol(df, "X.IS").reversals, [])


if __name__ == "__main__":
    unittest.main()
