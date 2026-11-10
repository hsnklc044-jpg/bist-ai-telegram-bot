"""/tablo: RSI, price against the EMA set, five-day volume and candle patterns, each rule on constructed data;
the command's four ways in (watchlist, saved screen, symbols, locks) on stand-ins."""

import asyncio
import contextlib
import unittest
from types import SimpleNamespace
from unittest import mock

import numpy as np
import pandas as pd

from core.analytics import symbol_table as T
from tests.test_scorecard import bars, trend


def candles(rows, quiet=40, price=10.0, spread=0.1):
    """`quiet` calm candles (range 2 x spread) followed by the given (open, high, low, close) rows."""

    base = [(price, price + spread, price - spread, price)] * quiet
    data = base + list(rows)
    return pd.DataFrame(data, columns=["open", "high", "low", "close"],
                        index=pd.bdate_range("2024-01-02", periods=len(data))).assign(volume=1e6)


class PriceVsEmaTest(unittest.TestCase):
    def test_above_all_below_all_and_mixed(self):
        self.assertEqual(T.price_vs_ema(trend(300)["close"]), "Tümü Üzerinde")
        self.assertEqual(T.price_vs_ema(trend(300, growth=0.997)["close"]), "Tümü Altında")
        close = trend(300)["close"].copy()
        close.iloc[-1] = close.iloc[-1] * 0.9  # a sharp last day: under the short EMAs, over the 200
        self.assertEqual(T.price_vs_ema(close), "Karışık")

    def test_short_history_is_missing_not_guessed(self):
        self.assertEqual(T.price_vs_ema(trend(100)["close"]), "veri yok")


class VolumeTest(unittest.TestCase):
    def series(self, recent, base, n=30):
        return pd.Series([base] * (n - 5) + [recent] * 5, dtype=float)

    def test_the_three_labels(self):
        self.assertEqual(T.volume_label(self.series(500, 1000)), "Ortalama Altında")
        self.assertEqual(T.volume_label(self.series(1200, 1000)), "Ortalama Üzerinde")
        self.assertEqual(T.volume_label(self.series(1600, 1000)), "Yüksek")

    def test_the_base_is_the_twenty_sessions_before_the_five(self):
        volume = pd.Series([1e9] * 10 + [1000.0] * 20 + [1200.0] * 5)  # old spike is outside both windows
        self.assertEqual(T.volume_label(volume), "Ortalama Üzerinde")

    def test_short_history_and_zero_base_are_missing(self):
        self.assertEqual(T.volume_label(pd.Series([1.0] * 20)), "veri yok")
        self.assertEqual(T.volume_label(self.series(5, 0)), "veri yok")


class PatternTest(unittest.TestCase):
    def test_bullish_engulfing_with_wicks_is_only_that(self):
        df = candles([(10.0, 10.1, 8.9, 9.0), (8.9, 10.9, 8.5, 10.2)])  # body 1.3 of range 2.4
        self.assertEqual(T.patterns(df), "Yutan Boğa")

    def test_bearish_engulfing_with_wicks(self):
        df = candles([(9.0, 10.1, 8.9, 10.0), (10.1, 10.6, 8.2, 8.8)])
        self.assertEqual(T.patterns(df), "Yutan Ayı")

    def test_a_bigger_body_is_required(self):
        df = candles([(10.0, 10.1, 8.9, 9.0), (9.0, 10.1, 8.9, 10.0)])  # covers the first body exactly: not larger
        self.assertNotIn("Yutan", T.patterns(df))
        bigger = candles([(10.0, 10.1, 8.9, 9.0), (9.0, 10.1, 8.9, 10.05)])
        self.assertIn("Yutan Boğa", T.patterns(bigger))

    def test_marubozu_up_and_down(self):
        up = candles([(9.9, 10.0, 9.9, 10.0), (10.0, 11.0, 10.0, 11.0)])  # the previous candle is also up: no engulfing
        down = candles([(10.1, 10.1, 10.0, 10.0), (10.0, 10.0, 9.0, 9.0)])
        self.assertEqual(T.patterns(up), "Yükseliş Marubozu")
        self.assertEqual(T.patterns(down), "Düşüş Marubozu")

    def test_a_tiny_marubozu_shaped_candle_does_not_count(self):
        df = candles([(10.0, 10.1, 10.0, 10.05), (10.05, 10.06, 10.05, 10.06)])  # range 0.01 of an ATR near 0.2
        self.assertEqual(T.patterns(df), "")

    def test_both_labels_and_none(self):
        both = candles([(10.0, 10.1, 9.0, 9.0), (8.9, 10.3, 8.9, 10.2)])
        self.assertEqual(T.patterns(both), "Yutan Boğa, Yükseliş Marubozu")
        self.assertEqual(T.patterns(candles([])), "")
        self.assertEqual(T.patterns(candles([], quiet=1)), "")


class RowTest(unittest.TestCase):
    def test_a_full_row(self):
        row = T.row("THYAO.IS", bars(300))
        self.assertTrue(0 < row.rsi < 100)
        self.assertIn(row.price_ema, ("Tümü Üzerinde", "Tümü Altında", "Karışık"))
        self.assertEqual(row.day, bars(300).index[-1].date())

    def test_short_or_missing_data_is_said(self):
        short = T.row("X.IS", bars(120))
        self.assertTrue(np.isnan(short.rsi))
        self.assertEqual(short.price_ema, "veri yok")
        self.assertEqual(T.row("Y.IS", None).volume, "veri yok")
        self.assertEqual(T.row("Y.IS", pd.DataFrame()).price_ema, "veri yok")

    def test_text_lines_footer_and_the_cap(self):
        table = [T.row(f"S{i:02d}.IS", bars(300, seed=i)) for i in range(T.MAX_ROWS + 3)]
        text = T.text("deneme", table)
        lines = text.splitlines()
        self.assertIn("Tablo: deneme", lines[0])
        self.assertEqual(len(lines), 1 + T.MAX_ROWS + 1 + 1)
        self.assertIn("ve 3 hisse daha", lines[-2])
        self.assertIn("öneri değildir", lines[-1])
        for word in (" al ", " sat ", "fırsat"):
            self.assertNotIn(word, text.lower())


class CommandTest(unittest.TestCase):
    def run_table(self, args, **patches):
        from bot import analysis
        from tests.test_screen_telegram import fake_update

        sent = []
        with contextlib.ExitStack() as stack:  # the stand-ins live for this one call only
            for target, kw in patches.items():
                stack.enter_context(mock.patch(target, **kw))
            asyncio.run(analysis.table_cmd(fake_update(sent), SimpleNamespace(args=args)))
        return sent[0][0]

    def test_registered_and_documented(self):
        from bot.handlers import COMMANDS, MENU
        from bot.start import HELP_TEXT

        self.assertIn("tablo", dict(COMMANDS))
        self.assertIn("tablo", dict(MENU))
        self.assertIn("/tablo", HELP_TEXT)

    def test_the_watchlist_when_no_argument(self):
        text = self.run_table([], **{"core.watchlist.service.get_watchlist": dict(return_value=["THYAO.IS"]),
                                     "core.reports.daily.adjusted_bars": dict(return_value=bars(300))})
        self.assertIn("Tablo: takip listen", text)
        self.assertIn("THYAO", text)

    def test_an_empty_watchlist_says_how_to_start(self):
        text = self.run_table([], **{"core.watchlist.service.get_watchlist": dict(return_value=[])})
        self.assertIn("Takip listen boş", text)

    def test_symbols_given(self):
        text = self.run_table(["THYAO", "GARAN"], **{"core.reports.daily.adjusted_bars": dict(return_value=bars(300))})
        self.assertIn("seçtiğin hisseler", text)
        self.assertIn("GARAN", text)

    def test_a_saved_screen_shows_its_matches_and_respects_the_lock(self):
        found = SimpleNamespace(matches=[SimpleNamespace(symbol="AAA.IS")])
        patches = {"core.screen.subscriptions.criteria_of": dict(return_value="rsi>0"),
                   "core.screen.command._live": dict(return_value=({"AAA.IS": bars(300)}, bars(300))),
                   "core.screen.universe.symbols": dict(return_value=["AAA.IS"]),
                   "core.screen.universe.suspects": dict(return_value=set()),
                   "core.screen.engine.run": dict(return_value=found),
                   "core.signals.store.locked": dict(return_value=False)}
        text = self.run_table(["deneme"], **patches)
        self.assertIn("Tablo: deneme", text)
        self.assertIn("AAA", text)
        patches["core.signals.store.locked"] = dict(return_value=True)
        self.assertIn("kilidi nedeniyle durdu", self.run_table(["deneme"], **patches))

    def test_a_screen_with_no_match_and_a_bad_symbol_and_a_failure(self):
        empty = SimpleNamespace(matches=[])
        patches = {"core.screen.subscriptions.criteria_of": dict(return_value="rsi>0"),
                   "core.screen.command._live": dict(return_value=({}, bars(300))),
                   "core.screen.universe.symbols": dict(return_value=[]),
                   "core.screen.universe.suspects": dict(return_value=set()),
                   "core.screen.engine.run": dict(return_value=empty),
                   "core.signals.store.locked": dict(return_value=False)}
        self.assertIn("koşulu sağlayan hisse yok", self.run_table(["deneme"], **patches))
        self.assertTrue(self.run_table(["!!"]))
        failing = {"core.reports.daily.adjusted_bars": dict(side_effect=RuntimeError("x"))}
        self.assertIn("hazırlanamadı", self.run_table(["THYAO"], **failing))


if __name__ == "__main__":
    unittest.main()
