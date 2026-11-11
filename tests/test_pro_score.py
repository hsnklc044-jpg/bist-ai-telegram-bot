"""Professional technical score (I, the user's 11.11.2026 decision; K-88). Written before the code and before any data.

Six dimensions, 100 points: long trend 20, medium momentum 20, relative strength 20, near the 52-week high 15,
short confirmation 15, volume confirmation 10. A dimension that cannot be computed is "veri yok": never counted as 0,
and the score then gets no colour. Volatility rank ≥ 90 adds a warning, not points. Fields come from
core/screen/fields.py (one calculation, one place). The user's scorecard is not touched."""

import math
import unittest

import pandas as pd

from core.analytics import pro_score as P

FULL = {
    "close": 110.0, "sma(200)": 100.0, "sma(50)": 105.0,
    "getiri_12a_1a_haric": 20.0, "getiri_6a_1a_haric": 5.0,
    "goreli_guc_yuzdelik": 75.0,
    "zirve_uzaklik": -8.0,
    "macd": 1.0, "macd_sinyal": 0.5, "rsi": 60.0, "ema20": 108.0,
    "obv_egim": 0.3, "cmf": 5.0,
    "oynaklik_sira": 50.0,
}


def row(**changes):
    values = dict(FULL)
    values.update(changes)
    return pd.Series(values, dtype=float)


class TotalTest(unittest.TestCase):
    def test_everything_met_is_100(self):
        got = P.score(row())
        self.assertEqual(got.total, 100)
        self.assertEqual(got.missing, [])
        self.assertEqual(got.label(), "100/100")
        self.assertEqual(got.colour(), ("🟢", "Güçlü"))

    def test_the_dimension_maxima_add_up_to_100(self):
        self.assertEqual(sum(d.maximum for d in P.DIMENSIONS), 100)
        self.assertEqual([d.maximum for d in P.DIMENSIONS], [20, 20, 20, 15, 15, 10])

    def test_never_above_100_or_below_0(self):
        for changes in ({}, {"close": 1.0, "sma(50)": 1.0, "getiri_12a_1a_haric": -50, "getiri_6a_1a_haric": -9,
                             "goreli_guc_yuzdelik": 1, "zirve_uzaklik": -90, "macd": -1, "rsi": 20, "obv_egim": -1,
                             "cmf": -5}):
            total = P.score(row(**changes)).total
            self.assertTrue(0 <= total <= 100, total)
        self.assertEqual(P.score(row(close=1.0, **{"sma(50)": 1.0}, getiri_12a_1a_haric=-50, getiri_6a_1a_haric=-9,
                                     goreli_guc_yuzdelik=1, zirve_uzaklik=-90, macd=-1, rsi=20, obv_egim=-1,
                                     cmf=-5)).total, 0)


class ThresholdTest(unittest.TestCase):
    def points(self, name, **changes):
        return P.score(row(**changes)).parts[name]

    def test_long_trend(self):
        self.assertEqual(self.points("Uzun vadeli trend", close=99.0), 10)
        self.assertEqual(self.points("Uzun vadeli trend", **{"sma(50)": 99.0}), 10)
        self.assertEqual(self.points("Uzun vadeli trend", close=99.0, **{"sma(50)": 99.0}), 0)

    def test_momentum(self):
        self.assertEqual(self.points("Orta vadeli momentum", getiri_12a_1a_haric=0.0), 10)  # > 0, not >= 0
        self.assertEqual(self.points("Orta vadeli momentum", getiri_6a_1a_haric=-1.0), 10)

    def test_relative_strength_bands(self):
        for rank, points in ((70, 20), (69.9, 10), (30, 10), (29.9, 0), (100, 20)):
            self.assertEqual(self.points("Göreli güç", goreli_guc_yuzdelik=rank), points, rank)

    def test_near_the_high(self):
        for distance, points in ((0, 15), (-10, 15), (-10.1, 7), (-25, 7), (-25.1, 0)):
            self.assertEqual(self.points("52 hafta zirvesine yakınlık", zirve_uzaklik=distance), points, distance)

    def test_short_confirmation(self):
        self.assertEqual(self.points("Kısa vadeli teyit", macd=0.4), 10)
        for rsi, points in ((50, 15), (70, 15), (49.9, 10), (70.1, 10)):
            self.assertEqual(self.points("Kısa vadeli teyit", rsi=rsi), points, rsi)
        self.assertEqual(self.points("Kısa vadeli teyit", ema20=111.0), 10)

    def test_volume_confirmation(self):
        self.assertEqual(self.points("Hacim teyidi", obv_egim=0.0), 5)
        self.assertEqual(self.points("Hacim teyidi", cmf=-1.0), 5)


class MissingTest(unittest.TestCase):
    def test_a_missing_dimension_is_not_zero_and_gets_no_colour(self):
        got = P.score(row(goreli_guc_yuzdelik=math.nan))
        self.assertIsNone(got.parts["Göreli güç"])
        self.assertEqual(got.missing, ["Göreli güç"])
        self.assertEqual(got.total, 80)
        self.assertEqual(got.label(), "80/100 (eksik boyut: Göreli güç)")
        self.assertIsNone(got.colour())

    def test_one_missing_input_makes_its_whole_dimension_missing(self):
        got = P.score(row(**{"sma(200)": math.nan}))
        self.assertIsNone(got.parts["Uzun vadeli trend"])

    def test_the_volatility_warning_is_not_points(self):
        calm, wild = P.score(row(oynaklik_sira=89)), P.score(row(oynaklik_sira=90))
        self.assertFalse(calm.warning)
        self.assertTrue(wild.warning)
        self.assertEqual(calm.total, wild.total)


class LatestTest(unittest.TestCase):
    def test_a_steady_riser_scores_high_and_a_faller_low(self):
        import numpy as np

        days = pd.bdate_range("2025-01-01", periods=320)

        def frame(drift):
            close = pd.Series(100 * np.exp(drift * np.arange(320)) * (1 + 0.01 * np.sin(np.arange(320))), index=days)
            return pd.DataFrame({"open": close, "high": close * 1.01, "low": close * 0.99, "close": close,
                                 "volume": 1000.0 + 10 * np.arange(320)})

        frames = {"UP": frame(0.002), "FLAT": frame(0.0), "DOWN": frame(-0.002)}
        got = P.latest(frames, frames["FLAT"]["close"])
        self.assertGreater(got["UP"].total, got["FLAT"].total)
        self.assertGreater(got["FLAT"].total, got["DOWN"].total)
        self.assertEqual(got["UP"].missing, [])


class SourceTest(unittest.TestCase):
    def test_the_inputs_are_screen_fields(self):
        from core.screen import fields

        for column in P.COLUMNS:
            name, _ = fields.split(column) if column != "close" else ("close", None)
            self.assertTrue(column == "close" or name in fields.FIELDS or column in fields.RANKED, column)

    def test_the_scorecard_is_untouched(self):
        from core.analytics import scorecard

        self.assertEqual(sum(points for _, _, points in scorecard.RULES), 100)
        self.assertEqual(len(scorecard.RULES), 12)


if __name__ == "__main__":
    unittest.main()
