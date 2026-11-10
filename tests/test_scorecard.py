"""/karne: the TradingView indicator scorecard. Each indicator is checked against the `ta` library (an independent
implementation), by hand on small windows and by behaviour on constructed trends; the command and its wiring too."""

import asyncio
import unittest
from types import SimpleNamespace
from unittest import mock

import numpy as np
import pandas as pd

from core.analytics import scorecard as S


def bars(n=600, drift=0.0004, vol=0.015, seed=3, volume=(1e6, 3e6), start="2023-01-02"):
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(drift, vol, n)))
    high = close * (1 + np.abs(rng.normal(0, 0.008, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.008, n)))
    return pd.DataFrame({"open": close, "high": high, "low": low, "close": close,
                         "volume": rng.integers(volume[0], volume[1], n).astype(float)},
                        index=pd.bdate_range(start, periods=n))


def trend(n=400, growth=1.003, volume_growth=True):
    close = 100 * growth ** np.arange(n)
    return pd.DataFrame({"open": close, "high": close * 1.005, "low": close * 0.995, "close": close,
                         "volume": (1e6 + 1e4 * np.arange(n)) if volume_growth else np.full(n, 1e6)},
                        index=pd.bdate_range("2023-01-02", periods=n))


class ParityWithTaTest(unittest.TestCase):
    df = bars()

    def close(self, ours, theirs, tolerance=1e-6, skip=300):
        a, b = ours.iloc[skip:].to_numpy(), theirs.iloc[skip:].to_numpy()
        np.testing.assert_allclose(a, b, atol=tolerance, rtol=0)

    def test_rsi(self):
        from ta.momentum import RSIIndicator

        self.close(S.rsi(self.df["close"]), RSIIndicator(self.df["close"], window=14).rsi())

    def test_macd(self):
        from ta.trend import MACD

        line, signal = S.macd(self.df["close"])
        ref = MACD(self.df["close"], window_slow=26, window_fast=12, window_sign=9)
        self.close(line, ref.macd())
        self.close(signal, ref.macd_signal())

    def test_cci(self):
        from ta.trend import CCIIndicator

        self.close(S.cci(self.df), CCIIndicator(self.df["high"], self.df["low"], self.df["close"], window=20).cci(),
                   tolerance=1e-6)

    def test_mfi(self):
        from ta.volume import MFIIndicator

        ref = MFIIndicator(self.df["high"], self.df["low"], self.df["close"], self.df["volume"], window=14)
        self.close(S.mfi(self.df), ref.money_flow_index(), tolerance=1e-6)

    def test_obv_differs_only_by_its_starting_constant(self):
        from ta.volume import OnBalanceVolumeIndicator

        ref = OnBalanceVolumeIndicator(self.df["close"], self.df["volume"]).on_balance_volume()
        offset = (S.obv(self.df) - ref).iloc[1:]
        self.assertLess(float(offset.max() - offset.min()), 1e-3)

    def test_atr_converges_to_the_same_value(self):
        from ta.volatility import AverageTrueRange

        ref = AverageTrueRange(self.df["high"], self.df["low"], self.df["close"], window=14).average_true_range()
        self.close(S.atr(self.df), ref, tolerance=1e-6)

    def test_directional_indicators_match_after_warm_up(self):
        from ta.trend import ADXIndicator

        ref = ADXIndicator(self.df["high"], self.df["low"], self.df["close"], window=14)
        plus, minus, _ = S.dmi(self.df)
        self.close(plus, ref.adx_pos(), tolerance=1e-3)
        self.close(minus, ref.adx_neg(), tolerance=1e-3)


class DefinitionTest(unittest.TestCase):
    def test_rma_is_wilder_smoothing(self):
        out = S.rma(pd.Series([1.0, 2, 3, 4, 5, 6]), 3)
        self.assertTrue(out.iloc[:2].isna().all())
        expected = 1.0
        for value in (2.0, 3.0):  # alpha = 1/3, first value as the seed
            expected = expected + (value - expected) / 3
        self.assertAlmostEqual(float(out.iloc[2]), expected)
        self.assertAlmostEqual(float(out.iloc[3]), expected + (4 - expected) / 3)

    def test_parabolic_sar_by_hand(self):
        df = pd.DataFrame({"high": [10, 11, 12, 12.5, 11.5], "low": [9, 10, 10.5, 11, 8.0],
                           "close": [9.5, 10.8, 11.8, 12.3, 8.5], "open": 0, "volume": 1},
                          index=pd.bdate_range("2024-01-01", periods=5))
        out = S.parabolic_sar(df)
        self.assertTrue(np.isnan(out.iloc[0]))
        # bar 1: SAR 9 + 0.02 (11 - 9) = 9.04, clamped to the previous low 9.0; bars 2, 3: AF 0.04, 0.06;
        # bar 4: the low 8.0 is under the SAR, so it flips to the extreme 12.5
        np.testing.assert_allclose(out.iloc[1:].to_numpy(), [9.0, 9.0, 9.12, 12.5])

    def test_sar_is_never_inside_the_previous_two_candles(self):
        for seed in range(6):
            df = bars(400, seed=seed)
            sar = S.parabolic_sar(df)
            below = df["close"] > sar
            for i in range(3, len(df)):
                if below.iloc[i]:
                    self.assertLessEqual(sar.iloc[i], min(df["low"].iloc[i - 1], df["low"].iloc[i - 2]) + 1e-9)
                else:
                    self.assertGreaterEqual(sar.iloc[i], max(df["high"].iloc[i - 1], df["high"].iloc[i - 2]) - 1e-9)

    def test_adx_is_the_sma_of_dx_not_wilders(self):
        df = bars(120, seed=5)
        plus, minus, adx = S.dmi(df)
        dx = 100 * (plus - minus).abs() / (plus + minus)
        np.testing.assert_allclose(adx.iloc[40:].to_numpy(), dx.rolling(14).mean().iloc[40:].to_numpy())

    def test_cci_by_hand(self):
        df = bars(40, seed=2)
        tp = ((df["high"] + df["low"] + df["close"]) / 3).iloc[-20:].to_numpy()
        expected = (tp[-1] - tp.mean()) / (0.015 * np.abs(tp - tp.mean()).mean())
        self.assertAlmostEqual(float(S.cci(df).iloc[-1]), float(expected), places=9)

    def test_mfi_by_hand(self):
        df = bars(30, seed=4)
        tp = ((df["high"] + df["low"] + df["close"]) / 3).to_numpy()
        flow = tp * df["volume"].to_numpy()
        up = sum(flow[i] for i in range(len(tp) - 14, len(tp)) if tp[i] > tp[i - 1])
        down = sum(flow[i] for i in range(len(tp) - 14, len(tp)) if tp[i] < tp[i - 1])
        self.assertAlmostEqual(float(S.mfi(df).iloc[-1]), 100 - 100 / (1 + up / down), places=9)

    def test_supertrend_follows_a_trend_and_flips(self):
        up = trend(200)
        self.assertEqual(float(S.supertrend(up).iloc[-1]), 1)
        down = trend(200, growth=0.997)
        self.assertEqual(float(S.supertrend(down).iloc[-1]), -1)
        flip = pd.concat([trend(120), trend(120, growth=0.99).set_axis(pd.bdate_range("2024-01-01", periods=120))])
        flip["close"] = np.r_[trend(120)["close"].to_numpy(), trend(120)["close"].iloc[-1] * 0.99 ** np.arange(1, 121)]
        flip["high"], flip["low"] = flip["close"] * 1.005, flip["close"] * 0.995
        self.assertEqual(float(S.supertrend(flip).iloc[-1]), -1)

    def test_rules_add_up_to_100(self):
        self.assertEqual(S.MAXIMUM, 100)
        self.assertEqual(len(S.RULES), 12)
        self.assertEqual([p for _, _, p in S.RULES], [5, 10, 10, 10, 5, 10, 10, 10, 10, 5, 10, 5])


class ScoreTest(unittest.TestCase):
    def test_a_smooth_uptrend_scores_every_trend_momentum_and_volume_rule(self):
        card = S.score(trend())
        bad = [r.name for r in card.rows if r.ok is False]
        self.assertEqual(bad, ["ATR (14 gün)"])  # a steady trend has no volatility expansion
        self.assertEqual((card.total, card.missing), (95, 0))

    def test_a_downtrend_scores_nothing_of_direction(self):
        card = S.score(trend(growth=0.997, volume_growth=False))
        # a constant-percent decline shrinks in price units, so the MACD line creeps above its signal: that is the
        # indicator's own arithmetic; every other rule (flat volume: RelVol 1.0 is not above 1) scores nothing
        self.assertEqual({r.name for r in card.rows if r.points}, {"MACD (çizgi)"})
        self.assertEqual(card.total, 10)

    def test_groups_add_up_and_the_total_is_the_sum_of_the_rows(self):
        card = S.score(bars())
        self.assertEqual(sum(got for got, _ in card.groups().values()), card.total)
        self.assertEqual(sum(top for _, top in card.groups().values()), 100)
        self.assertEqual(card.total, sum(r.points for r in card.rows))

    def test_short_history_is_data_missing_not_zero_by_stealth(self):
        card = S.score(bars(100))
        self.assertEqual((card.total, card.missing), (0, 12))
        self.assertTrue(all(r.ok is None for r in card.rows))
        self.assertIn("veri yok: 12", S.text("X.IS", bars(100)))

    def test_flat_prices_do_not_crash_and_the_undefined_indicators_are_missing(self):
        n = 300
        df = pd.DataFrame({"open": 10.0, "high": 10.0, "low": 10.0, "close": 10.0, "volume": 1e6},
                          index=pd.bdate_range("2023-01-02", periods=n))
        card = S.score(df)
        by_name = {r.name: r for r in card.rows}
        self.assertIsNone(by_name["CCI (-100 üstü)"].ok)
        self.assertIsNone(by_name["RSI (50 üstü)"].ok)
        self.assertEqual(card.total, sum(r.points for r in card.rows))

    def test_the_card_reads_the_last_closed_candle_only(self):
        df = bars()
        whole, cut = S.score(df), S.score(df.iloc[:-1])
        self.assertEqual(whole.day, df.index[-1].date())
        self.assertEqual(cut.day, df.index[-2].date())

    def test_text_is_information_not_a_call(self):
        text = S.text("THYAO.IS", bars())
        self.assertIn("THYAO teknik gösterge karnesi", text)
        self.assertRegex(text, r"Toplam: \d+/100")
        self.assertIn("öneri değildir", text)
        for word in (" al ", " sat ", "fırsat"):
            self.assertNotIn(word, text.lower())
        self.assertEqual(text.count("✅") + text.count("❌") + text.count("❔"), 12)


class CommandTest(unittest.TestCase):
    def test_the_command_is_registered_and_documented(self):
        from bot.handlers import COMMANDS, MENU
        from bot.start import HELP_TEXT

        self.assertIn("karne", dict(COMMANDS))
        self.assertIn("karne", dict(MENU))
        self.assertIn("/karne THYAO", HELP_TEXT)

    def run_command(self, args, bars_value=None, error=None):
        from bot import analysis
        from tests.test_screen_telegram import fake_update

        sent = []
        patch = mock.patch("core.reports.daily.adjusted_bars", return_value=bars_value, side_effect=error)
        with patch:
            asyncio.run(analysis.scorecard_cmd(fake_update(sent), SimpleNamespace(args=args)))
        return sent

    def test_a_symbol_returns_the_card(self):
        sent = self.run_command(["THYAO"], bars())
        self.assertIn("THYAO teknik gösterge karnesi", sent[0][0])

    def test_usage_and_a_bad_symbol(self):
        self.assertIn("/karne THYAO", self.run_command([])[0][0])
        self.assertTrue(self.run_command(["!!"])[0][0])

    def test_no_data_and_a_failure_are_said_not_hidden(self):
        self.assertIn("fiyat verisi yok", self.run_command(["THYAO"], pd.DataFrame())[0][0])
        self.assertIn("hesaplanamadı", self.run_command(["THYAO"], error=ValueError("x"))[0][0])


if __name__ == "__main__":
    unittest.main()
