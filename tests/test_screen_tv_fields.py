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
            self.assertIn("geçerli değerler: 5, 10, 20, 40, 50, 100, 200", str(caught.exception))


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
