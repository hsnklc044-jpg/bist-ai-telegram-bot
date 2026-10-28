"""
Özellik A §2.3: the /tara fields from the levels (K-49), computed day by day without look-ahead:
destek_uzaklik_atr, direnc_uzaklik_atr, seviye_gucu (of the nearest cluster level) and the breaks
kirdi_yukari(direnc) / kirdi_asagi(destek). Each day equals levels() on the candles cut at that day.
"""

import unittest

import numpy as np
import pandas as pd

from core.analytics import levels as L
from core.screen import engine, fields
from core.screen.language import parse
from tests.test_levels import market


class SeriesTest(unittest.TestCase):
    def test_every_day_equals_the_cut_computation(self):
        df = market(330, seed=5)
        series = L.daily_series(df)
        for day in df.index[-60::7]:
            cut = L.levels(df.loc[:day])
            clusters = [lv for lv in cut if lv.method == "küme"]
            supports = [lv for lv in clusters if lv.kind == "destek"]
            resistances = [lv for lv in clusters if lv.kind == "direnç"]
            with self.subTest(day=day):
                row = series.loc[day]
                if supports:
                    self.assertAlmostEqual(row["destek_uzaklik_atr"], max(supports, key=lambda lv: lv.price).dist_atr)
                if resistances:
                    self.assertAlmostEqual(row["direnc_uzaklik_atr"], min(resistances, key=lambda lv: lv.price).dist_atr)
                nearest = min(clusters, key=lambda lv: abs(lv.dist_atr))
                self.assertEqual(row["seviye_gucu"], nearest.strength)

    def test_no_look_ahead(self):
        df = market(330, seed=6)
        cut = 280
        before = L.daily_series(df.iloc[:cut])
        later = df.copy()
        later.iloc[cut:, :4] *= 2.5
        pd.testing.assert_frame_equal(L.daily_series(later).iloc[:cut], before)

    def test_recent_days_only(self):
        df = market(330, seed=8)
        full, recent = L.daily_series(df), L.daily_series(df, recent=64)
        pd.testing.assert_frame_equal(recent.iloc[-64:], full.iloc[-64:])
        self.assertTrue(recent.iloc[:-64].isna().all().all())

    def test_breaks(self):
        df = market(330, seed=7)
        s = L.daily_series(df)
        close, atr = df["close"], L.atr(df)
        for day in s.index[s["kirdi_yukari"] == 1][:5]:
            i = df.index.get_loc(day)
            prev_res = s["direnc_uzaklik_atr"].iloc[i - 1] * atr.iloc[i - 1] + close.iloc[i - 1]
            with self.subTest(day=day):
                self.assertGreater(close.iloc[i], prev_res + 0.5 * atr.iloc[i])
        self.assertTrue(set(s["kirdi_yukari"].dropna().unique()) <= {0.0, 1.0})


class TaraTest(unittest.TestCase):
    def test_fields_and_the_break_syntax(self):
        q = parse("kirdi_yukari(direnc) destek_uzaklik_atr>-2 seviye_gucu>=20")
        self.assertEqual(q.text, "kirdi_yukari(direnc) ve destek_uzaklik_atr>-2 ve seviye_gucu>=20")
        self.assertEqual(parse(q.text).text, q.text)
        self.assertIn("kirdi_yukari", q.fields)
        self.assertIn("kirdi_asagi", parse("kirdi_asagi(destek)").fields)
        for bad in ("kirdi_yukari(destek)", "kirdi_asagi(direnc)", "kirdi_yukari"):
            with self.subTest(bad), self.assertRaises(Exception):
                parse(bad)

    def test_engine_and_table(self):
        frames = {f"S{i:02d}.IS": market(330, seed=20 + i) for i in range(4)}
        bench = market(330, seed=99)
        t = fields.table(frames["S00.IS"], bench["close"], ["destek_uzaklik_atr", "kirdi_yukari"])
        pd.testing.assert_series_equal(t["destek_uzaklik_atr"], L.daily_series(frames["S00.IS"])["destek_uzaklik_atr"],
                                       check_names=False)
        result = engine.run(parse("direnc_uzaklik_atr>0 ele=hayir"), frames, bench, actions=[])
        self.assertEqual(len(result.matches) + len(result.missing), 4)
        self.assertTrue(all(np.isfinite(m.values["direnc_uzaklik_atr"]) for m in result.matches))


if __name__ == "__main__":
    unittest.main()
