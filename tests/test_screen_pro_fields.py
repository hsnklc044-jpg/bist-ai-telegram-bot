"""
Profesyonel filtreler, Aşama 2 (DECISIONS K-47): the fields the technical professional templates
need, each equal to a hand (or ta) computation, and the cross-sectional ranks computed the same
way in the live list, the card and /tara_aciklama.
"""

import math
import unittest

import numpy as np
import pandas as pd

from core.screen import engine, fields
from core.screen.language import ScreenError, parse
from tests.test_screen_engine import walk


class FieldTest(unittest.TestCase):
    def setUp(self):
        self.df, self.bench = walk(600, 0.0004, 31, volume=3e7), walk(600, 0.0, 32)

    def table(self, *names):
        return fields.table(self.df, self.bench["close"], list(names))

    def test_each_field_equals_its_definition(self):
        from ta.trend import SMAIndicator

        c, h, low = self.df["close"], self.df["high"], self.df["low"]
        t = self.table("sma(150)", "zirve_52h", "dip_52h", "zirve_52h_oran", "dip_52h_oran", "getiri_6a_1a_haric",
                       "getiri_12a_1a_haric", "oynaklik_60g", "rs_puan", "egim(sma(200),21)")
        pd.testing.assert_series_equal(t["sma(150)"], SMAIndicator(c, window=150).sma_indicator().round(4),
                                       check_names=False)
        pd.testing.assert_series_equal(t["zirve_52h"], h.rolling(252, min_periods=252).max(), check_names=False)
        pd.testing.assert_series_equal(t["dip_52h"], low.rolling(252, min_periods=252).min(), check_names=False)
        pd.testing.assert_series_equal(t["zirve_52h_oran"], c / h.rolling(252, min_periods=252).max() * 100,
                                       check_names=False)
        pd.testing.assert_series_equal(t["dip_52h_oran"], c / low.rolling(252, min_periods=252).min() * 100,
                                       check_names=False)
        pd.testing.assert_series_equal(t["getiri_6a_1a_haric"], (c.shift(21) / c.shift(126) - 1) * 100,
                                       check_names=False)
        pd.testing.assert_series_equal(t["getiri_12a_1a_haric"], (c.shift(21) / c.shift(252) - 1) * 100,
                                       check_names=False)
        pd.testing.assert_series_equal(t["oynaklik_60g"], c.pct_change().rolling(60).std() * math.sqrt(252) * 100,
                                       check_names=False)
        r = {n: (c / c.shift(n) - 1) * 100 for n in (63, 126, 189, 252)}
        pd.testing.assert_series_equal(t["rs_puan"], 0.4 * r[63] + 0.2 * r[126] + 0.2 * r[189] + 0.2 * r[252],
                                       check_names=False)
        sma200 = SMAIndicator(c, window=200).sma_indicator().round(4)
        pd.testing.assert_series_equal(t["egim(sma(200),21)"], (sma200 / sma200.shift(21) - 1) * 100,
                                       check_names=False)

    def test_last_row_by_hand(self):
        c = self.df["close"].to_numpy()
        t = self.table("getiri_6a_1a_haric", "zirve_52h_oran")
        self.assertAlmostEqual(t["getiri_6a_1a_haric"].iloc[-1], (c[-22] / c[-127] - 1) * 100)
        high = self.df["high"].to_numpy()[-252:].max()
        self.assertAlmostEqual(t["zirve_52h_oran"].iloc[-1], c[-1] / high * 100)


class LanguageTest(unittest.TestCase):
    def test_slope_and_periods(self):
        q = parse("egim(sma200,21)>0 kapanis>sma150")
        self.assertIn("egim(sma(200),21)", q.fields)
        self.assertIn("sma(200)", q.fields)
        self.assertIn("sma(150)", q.fields)
        self.assertEqual(q.text, "egim(sma(200),21)>0 ve kapanis>sma(150)")
        self.assertEqual(parse(q.text).text, q.text)
        for bad in ("egim(5,21)>0", "egim(sma200)>0", "egim(sma200,1)>0", "egim(sma(30),21)>0"):
            with self.subTest(text=bad), self.assertRaises(ScreenError):
                parse(bad)


class RankTest(unittest.TestCase):
    def market(self):
        frames = {f"S{i:02d}.IS": walk(400, 0.0002 * (i - 10), 40 + i, volume=3e7) for i in range(20)}
        frames["CALM.IS"] = walk(400, 0.0, 99, volume=3e7)
        frames["CALM.IS"][["open", "high", "low", "close"]] = (
            frames["CALM.IS"][["open", "high", "low", "close"]] * 0 + 100 + np.sin(np.arange(400))[:, None] * 0.01)
        return frames, walk(400, 0.0, 7)

    def test_ranks_inside_the_scanned_list(self):
        frames, bench = self.market()
        for column in ("goreli_guc_yuzdelik", "momentum_sira", "oynaklik_sira", "gg_sira"):
            with self.subTest(column):
                result = engine.run(parse(f"{column}>=0 ele=hayir"), frames, bench, actions=[])
                values = sorted(m.values[column] for m in result.matches)
                self.assertEqual(len(values), 21)
                self.assertAlmostEqual(values[-1], 100.0)
        calm = engine.run(parse("oynaklik_sira<=5 ele=hayir"), frames, bench, actions=[])
        self.assertEqual([m.symbol for m in calm.matches], ["CALM.IS"])

    def test_card_ranks_each_day(self):
        from core.screen import card

        frames, bench = self.market()
        tables = card._tables(parse("momentum_sira>=80"), frames, bench, None)
        panel = pd.DataFrame({s: t["momentum_sira"] for s, t in tables.items()}).dropna()
        self.assertTrue(((panel.max(axis=1) - 100).abs() < 1e-9).all())


if __name__ == "__main__":
    unittest.main()
