"""/uzun: the 6-12 month model's technical score and the entry decision kept apart from it."""

import asyncio
import unittest
from types import SimpleNamespace
from unittest import mock

import pandas as pd

from core.analytics import long_model as M
from tests.test_scorecard import bars, trend


def breakout_frame():
    """A smooth uptrend whose last day closes 4% higher on three times the volume."""

    df = trend(400)
    last, before = df.index[-1], df.index[-2]
    df.loc[last, "open"] = df.loc[before, "close"]
    df.loc[last, "close"] = df.loc[before, "close"] * 1.04
    df.loc[last, "high"] = df.loc[last, "close"] * 1.002
    df.loc[last, "low"] = df.loc[before, "close"]
    df.loc[last, "volume"] = df.loc[before, "volume"] * 3
    return df


class ScoreTest(unittest.TestCase):
    def test_the_rules_are_40_25_35(self):
        self.assertEqual(M.MAXIMUM, 100)
        by_group = {}
        for _, group, points in M.RULES:
            by_group[group] = by_group.get(group, 0) + points
        self.assertEqual(by_group, {"Trend": 40, "Momentum": 25, "Hacim": 35})

    def test_a_high_score_without_a_breakout_is_watch_and_says_what_is_missing(self):
        result = M.evaluate(trend(400))
        self.assertGreaterEqual(result.card.total, 80)
        self.assertEqual(result.status, M.WATCH)
        self.assertIn("Kırılım", result.why)
        self.assertIn("Göreceli hacim", result.why)

    def test_the_entry_needs_all_four_conditions(self):
        df = breakout_frame()
        self.assertEqual(M.evaluate(df, upper=1e9).status, M.ENTER)
        above = M.evaluate(df, upper=float(df["close"].iloc[-1]) * 0.9)
        self.assertEqual((above.status, above.card.total), (M.WATCH, M.evaluate(df).card.total))
        self.assertIn("üst alım", above.why)
        unknown = M.evaluate(df)
        self.assertEqual(unknown.status, M.WATCH)
        self.assertIn("üst alım fiyatı girilmedi", unknown.why)

    def test_the_score_is_the_same_with_or_without_the_price_cap(self):
        df = breakout_frame()
        self.assertEqual(M.evaluate(df, upper=1e9).card.total, M.evaluate(df, upper=1.0).card.total)

    def test_short_history_is_data_missing(self):
        result = M.evaluate(bars(150))
        self.assertEqual((result.status, result.card.total, result.card.missing), (M.LACKING, 0, 11))
        self.assertIn("150 mum var", result.why)

    def test_missing_indicators_are_not_rescaled(self):
        n = 300
        flat = pd.DataFrame({"open": 10.0, "high": 10.0, "low": 10.0, "close": 10.0, "volume": 1e6},
                            index=pd.bdate_range("2023-01-02", periods=n))
        card = M.evaluate(flat).card
        missing_max = sum(r.maximum for r in card.rows if r.ok is None)
        self.assertGreater(missing_max, 0)
        self.assertLessEqual(card.total, 100 - missing_max)
        self.assertEqual(card.total, sum(r.points for r in card.rows))

    def test_relative_volume_uses_the_median_and_leaves_today_out(self):
        df = trend(300)
        df.iloc[-6, df.columns.get_loc("volume")] = 1e12  # one outlier inside the 20 sessions: the median ignores it
        df["volume"] = df["volume"].astype(float)
        df.iloc[-21:-1, df.columns.get_loc("volume")] = 1000.0
        df.iloc[-6, df.columns.get_loc("volume")] = 1e12
        df.iloc[-1, df.columns.get_loc("volume")] = 1600.0
        row = next(r for r in M.evaluate(df).card.rows if r.name.startswith("Göreceli hacim"))
        self.assertTrue(row.ok)
        self.assertIn("1,60×", row.value)

    def test_todays_own_high_does_not_make_a_breakout(self):
        df = breakout_frame()
        df.loc[df.index[-1], "close"] = df["close"].iloc[-2] * 1.001  # closes under the earlier highs
        df.loc[df.index[-1], "high"] = df["close"].iloc[-2] * 1.5  # a huge spike high today
        breakout = M.evaluate(df, upper=1e9).conditions[1]
        self.assertFalse(breakout.ok)

    def test_the_adx_here_is_wilders(self):
        plus, minus, adx = M._wilder_adx(trend(300))
        self.assertGreater(plus, minus)
        self.assertGreater(adx, 20)


class DecisionTest(unittest.TestCase):
    def conditions(self, *values):
        return [M.Condition(f"k{i}", v, "") for i, v in enumerate(values)]

    def test_each_case(self):
        self.assertEqual(M.decide(self.conditions(True, True, True, True))[0], M.ENTER)
        self.assertEqual(M.decide(self.conditions(True, None, True, True))[0], M.LACKING)
        status, why = M.decide(self.conditions(True, False, True, True))
        self.assertEqual((status, why), (M.WATCH, "eksik: k1"))
        status, why = M.decide(self.conditions(True, True, True, None))
        self.assertEqual((status, "bilinmiyor: k3" in why), (M.WATCH, True))

    def test_the_text_keeps_score_and_decision_apart_and_names_the_gaps(self):
        text = M.text("THYAO.IS", trend(400), upper=None)
        self.assertIn("Teknik puan:", text)
        self.assertIn("Giriş koşulları (puandan ayrı):", text)
        self.assertIn("Temel filtre: değerlendirilmedi", text)
        self.assertIn("Karar: İzle", text)
        self.assertIn("öneri değildir", text)
        for word in (" al ", " sat ", "fırsat"):
            self.assertNotIn(word, text.lower())


class CommandTest(unittest.TestCase):
    def run_command(self, args, bars_value=None, error=None):
        from bot import analysis
        from tests.test_screen_telegram import fake_update

        sent = []
        with mock.patch("core.reports.daily.adjusted_bars", return_value=bars_value, side_effect=error):
            asyncio.run(analysis.long_cmd(fake_update(sent), SimpleNamespace(args=args)))
        return sent[0][0]

    def test_registered_and_documented(self):
        from bot.handlers import COMMANDS, MENU
        from bot.start import HELP_TEXT

        self.assertIn("uzun", dict(COMMANDS))
        self.assertIn("uzun", dict(MENU))
        self.assertIn("/uzun THYAO", HELP_TEXT)

    def test_with_and_without_the_upper_price(self):
        self.assertIn("üst alım fiyatı girilmedi", self.run_command(["THYAO"], breakout_frame()))
        self.assertIn("Karar: Giriş adayı", self.run_command(["THYAO", "1000000"], breakout_frame()))
        self.assertIn("Karar: Giriş adayı", self.run_command(["THYAO", "1000000,5"], breakout_frame()))

    def test_usage_and_bad_input(self):
        self.assertIn("/uzun THYAO 250", self.run_command([]))
        self.assertIn("Fiyat sayı olmalı", self.run_command(["THYAO", "abc"]))
        self.assertIn("sıfırdan büyük", self.run_command(["THYAO", "0"]))
        self.assertTrue(self.run_command(["!!"]))

    def test_no_data_and_a_failure_are_said(self):
        self.assertIn("fiyat verisi yok", self.run_command(["THYAO"], pd.DataFrame()))
        self.assertIn("hesaplanamadı", self.run_command(["THYAO"], error=ValueError("x")))


if __name__ == "__main__":
    unittest.main()
