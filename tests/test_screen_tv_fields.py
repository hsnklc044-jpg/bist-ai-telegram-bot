"""
/tara with the user's TradingView vocabulary (görev 28.10, Aşama A): fields named as TradingView
names them, each equal to the library or to a hand computation; crosses with a constant;
ema/sma limited to the periods the screens use; a 400-character input.
"""

import unittest

import numpy as np
import pandas as pd

from core.screen import fields
from core.screen.language import MAX_LENGTH, ScreenError, parse
from core.strategy.score import volume_ratio_series
from tests.test_screen_engine import walk


class TradingViewFieldsTest(unittest.TestCase):
    def setUp(self):
        self.df, self.bench = walk(400, 0.0004, 21, volume=3e7), walk(400, 0.0, 22)

    def table(self, *names):
        return fields.table(self.df, self.bench["close"], list(names))

    def test_each_field_equals_its_definition(self):
        from ta.momentum import StochasticOscillator
        from ta.trend import CCIIndicator

        t = self.table("goreli_hacim", "momentum10", "vwma20", "ortalama_hacim_30g", "likidite", "degisim_1h",
                       "degisim_1a", "degisim_3a", "zirve_1a", "stok_k", "stok_d", "cci")
        c, h, v = self.df["close"], self.df["high"], self.df["volume"]
        pd.testing.assert_series_equal(t["goreli_hacim"], volume_ratio_series(v, 10), check_names=False)
        pd.testing.assert_series_equal(t["momentum10"], c - c.shift(10), check_names=False)
        pd.testing.assert_series_equal(t["vwma20"], (c * v).rolling(20).sum() / v.rolling(20).sum(), check_names=False)
        pd.testing.assert_series_equal(t["ortalama_hacim_30g"], v.rolling(30).mean(), check_names=False)
        pd.testing.assert_series_equal(t["likidite"], (c * v).rolling(20).mean(), check_names=False)
        for name, n in (("degisim_1h", 5), ("degisim_1a", 21), ("degisim_3a", 63)):
            pd.testing.assert_series_equal(t[name], (c / c.shift(n) - 1) * 100, check_names=False)
        pd.testing.assert_series_equal(t["zirve_1a"], h.rolling(21).max(), check_names=False)
        stoch = StochasticOscillator(h, self.df["low"], c, window=14, smooth_window=3)
        pd.testing.assert_series_equal(t["stok_k"], stoch.stoch(), check_names=False)
        pd.testing.assert_series_equal(t["stok_d"], stoch.stoch_signal(), check_names=False)
        pd.testing.assert_series_equal(t["cci"], CCIIndicator(h, self.df["low"], c, window=20).cci(),
                                       check_names=False)

    def test_cmf_by_hand(self):
        # BIST 30 hedefi (03.11): Chaikin para akışı, 20 gün; a flat candle (high = low) adds no flow
        from ta.volume import ChaikinMoneyFlowIndicator

        c, h, low, v = self.df["close"], self.df["high"], self.df["low"], self.df["volume"]
        mfm = ((c - low) - (h - c)) / (h - low)
        expected = (mfm.fillna(0.0) * v).rolling(20).sum() / v.rolling(20).sum() * 100
        t = self.table("cmf")
        pd.testing.assert_series_equal(t["cmf"], expected, check_names=False)
        lib = ChaikinMoneyFlowIndicator(h, low, c, v, window=20).chaikin_money_flow() * 100
        np.testing.assert_allclose(t["cmf"].iloc[-100:], lib.iloc[-100:])
        self.assertTrue(t["cmf"].dropna().between(-100, 100).all())

    def test_twenty_day_volume_ratio_stays_separate(self):
        t = self.table("hacim_oran", "goreli_hacim")
        self.assertFalse(np.allclose(t["hacim_oran"].iloc[-50:], t["goreli_hacim"].iloc[-50:]))


class CrossWithConstantTest(unittest.TestCase):
    def test_true_only_on_the_crossing_day(self):
        index = pd.bdate_range("2026-01-05", periods=6)
        t = pd.DataFrame({"rsi": [45.0, 48.0, 52.0, 55.0, 49.0, 51.0]}, index=index)
        self.assertEqual(list(parse("kesti_yukari(rsi,50)").mask(t)), [False, False, True, False, False, True])
        self.assertEqual(list(parse("kesti_asagi(rsi,50)").mask(t)), [False, False, False, False, True, False])
        self.assertEqual(list(parse("son(3, kesti_yukari(rsi,50))").mask(t)), [False, False, True, True, True, True])


class PeriodTest(unittest.TestCase):
    def test_allowed_periods(self):
        for text in ("ema5>ema20", "ema(10)>ema(40)", "sma100<kapanis", "kapanis>ema200", "ema(200)>sma(50)"):
            with self.subTest(text=text):
                parse(text)

    def test_other_periods_are_refused_with_the_list(self):
        for text in ("ema7>ema20", "ema(30)>0", "sma(15)<kapanis"):
            with self.subTest(text=text), self.assertRaises(ScreenError) as caught:
                parse(text)
            self.assertIn("geçerli değerler: 5, 10, 14, 20, 40, 50, 100, 150, 200", str(caught.exception))


class RoketFieldsTest(unittest.TestCase):
    """K-86: the fields of the user's 'roket' screen, each by its TradingView definition and from
    closed candles only (a later candle never changes an earlier value)."""

    NEW = ("ichimoku_donusum", "ichimoku_baz", "ichimoku_a", "ichimoku_b", "aroon_yukari", "vwap", "pivot_fib",
           "bb_orta")

    def setUp(self):
        self.df, self.bench = walk(400, 0.0004, 31, volume=3e7), walk(400, 0.0, 32)

    def table(self, df=None):
        df = self.df if df is None else df
        return fields.table(df, self.bench["close"].reindex(df.index), list(self.NEW))

    @staticmethod
    def mid(df, end, n):
        window = df.iloc[end - n + 1:end + 1]
        return (window["high"].max() + window["low"].min()) / 2

    def test_ichimoku_by_hand_and_displaced_25_sessions(self):
        t, df = self.table(), self.df
        i = 300
        self.assertAlmostEqual(t["ichimoku_donusum"].iloc[i], self.mid(df, i, 9))
        self.assertAlmostEqual(t["ichimoku_baz"].iloc[i], self.mid(df, i, 26))
        j = i - 25  # today's cloud was computed 25 sessions ago
        self.assertAlmostEqual(t["ichimoku_a"].iloc[i], (self.mid(df, j, 9) + self.mid(df, j, 26)) / 2)
        self.assertAlmostEqual(t["ichimoku_b"].iloc[i], self.mid(df, j, 52))
        self.assertTrue(t["ichimoku_b"].iloc[:76].isna().all())  # 52 candles, then 25 ahead
        self.assertFalse(np.isnan(t["ichimoku_b"].iloc[76]))

    def test_vwap_and_bollinger_basis(self):
        t, df = self.table(), self.df
        pd.testing.assert_series_equal(t["vwap"], (df["high"] + df["low"] + df["close"]) / 3, check_names=False)
        np.testing.assert_allclose(t["bb_orta"].iloc[19:], df["close"].rolling(20).mean().iloc[19:])

    def test_aroon_up(self):
        index = pd.bdate_range("2026-01-05", periods=30)
        high = pd.Series(1.0, index=index)

        def up(h):
            df = pd.DataFrame({"open": 1.0, "high": h, "low": 0.5, "close": 1.0, "volume": 1.0}, index=index)
            return fields.table(df, df["close"], ["aroon_yukari"])["aroon_yukari"]

        self.assertTrue(up(high).iloc[:14].isna().all())
        self.assertAlmostEqual(up(high).iloc[-1], 100.0)  # every high equal: the newest counts
        newest = high.copy()
        newest.iloc[-1] = 5.0
        self.assertAlmostEqual(up(newest).iloc[-1], 100.0)
        oldest = high.copy()
        oldest.iloc[-15] = 5.0  # 14 sessions ago, the oldest candle of the 15
        self.assertAlmostEqual(up(oldest).iloc[-1], 0.0)
        seven = high.copy()
        seven.iloc[-8] = 5.0
        self.assertAlmostEqual(up(seven).iloc[-1], 50.0)
        t = self.table()
        self.assertTrue(t["aroon_yukari"].dropna().between(0, 100).all())

    def test_pivot_is_the_previous_month(self):
        t, df = self.table(), self.df
        first = df.index[0].to_period("M")
        self.assertTrue(t.loc[df.index.to_period("M") == first, "pivot_fib"].isna().all())
        month = df.index.to_period("M").unique()[3]
        prev = df[df.index.to_period("M") == month - 1]
        expected = (prev["high"].max() + prev["low"].min() + prev["close"].iloc[-1]) / 3
        days = t.loc[df.index.to_period("M") == month, "pivot_fib"]
        np.testing.assert_allclose(days.to_numpy(), expected)

    def test_a_missing_month_leaves_the_pivot_unknown(self):
        months = self.df.index.to_period("M")
        gap = months.unique()[4]
        df = self.df[months != gap]
        t = self.table(df)
        after = t.loc[df.index.to_period("M") == gap + 1, "pivot_fib"]
        self.assertTrue(len(after) > 0 and after.isna().all())

    def test_closed_candles_only(self):
        cut = 250
        full = self.table()
        past = self.table(self.df.iloc[:cut + 1])
        pd.testing.assert_frame_equal(full.iloc[:cut + 1], past)

    def test_ema14_is_allowed(self):
        self.assertIn("ema(14)", parse("kapanis>ema14").fields)


class LengthTest(unittest.TestCase):
    def test_four_hundred_characters(self):
        self.assertEqual(MAX_LENGTH, 400)
        ok = " ".join(["rsi 30..70"] * 15)
        self.assertLessEqual(len(ok), 400)
        parse(ok)
        with self.assertRaises(ScreenError) as caught:
            parse("rsi<30 " + "x" * 400)
        self.assertIn("en fazla 400 karakter", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
