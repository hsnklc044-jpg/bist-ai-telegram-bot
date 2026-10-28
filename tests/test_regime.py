"""
Talimat C §C1.3 (DECISIONS K-51): the market regime is a fixed, pre-written label, never a
signal. trend = XU100 vs its 200-session average; volatility = the 20-session standard deviation
of log returns, as a percentile of the previous 252 sessions; breadth = share of the day's BIST
100 members closing above their own EMA50.
"""

import unittest
from datetime import date

import numpy as np
import pandas as pd

from core.market import regime as R


def series(values, start="2024-01-01"):
    return pd.Series(np.asarray(values, dtype=float), index=pd.bdate_range(start, periods=len(values)))


def frame(close):
    return pd.DataFrame({"open": close, "high": close, "low": close, "close": close, "volume": 1e6})


class LabelTest(unittest.TestCase):
    def test_rules(self):
        self.assertEqual(R.label("üstünde", 85.0, 0.30), "yüksek oynaklık")  # first, whatever else
        self.assertEqual(R.label("üstünde", 50.0, 0.50), "yükseliş")
        self.assertEqual(R.label("altında", 50.0, 0.49), "düşüş")
        self.assertEqual(R.label("üstünde", 50.0, 0.40), "karışık")
        self.assertEqual(R.label("altında", 50.0, 0.70), "karışık")
        self.assertEqual(R.label(None, 50.0, 0.70), "bilinmiyor")
        self.assertEqual(R.label("üstünde", None, 0.70), "bilinmiyor")
        self.assertEqual(R.label("üstünde", 50.0, None), "bilinmiyor")


class ComponentTest(unittest.TestCase):
    def test_trend_by_hand(self):
        close = series(np.linspace(100, 200, 260))
        parts = R.components(close, {}, None)
        self.assertTrue(np.isnan(parts["sma200"].iloc[198]))  # 199 sessions are not enough
        self.assertAlmostEqual(parts["sma200"].iloc[-1], close.iloc[-200:].mean())
        self.assertEqual(parts["trend"].iloc[-1], "üstünde")

    def test_volatility_percentile_by_hand(self):
        rng = np.random.default_rng(0)
        returns = np.r_[rng.normal(0, 0.01, 300), rng.normal(0, 0.05, 20)]  # a calm year, then a storm
        close = series(100 * np.exp(np.cumsum(returns)))
        parts = R.components(close, {}, None)
        vol = np.log(close).diff().rolling(20).std()
        day = len(close) - 1
        prior = vol.iloc[day - 252:day]
        self.assertAlmostEqual(parts["vol_pct"].iloc[day], (prior <= vol.iloc[day]).mean() * 100)
        self.assertGreaterEqual(parts["vol_pct"].iloc[day], 80)
        self.assertTrue(np.isnan(parts["vol_pct"].iloc[20 + 251]))  # needs 252 earlier values

    def test_breadth_by_hand(self):
        index = pd.bdate_range("2024-01-01", periods=80)
        frames = {}
        for i in range(25):  # 15 rise (end above their EMA50), 10 fall (end below)
            path = np.linspace(100, 150, 80) if i < 15 else np.linspace(150, 100, 80)
            frames[f"S{i}.IS"] = frame(pd.Series(path, index=index))
        bench = pd.Series(100.0, index=index)
        parts = R.components(bench, frames, None)
        self.assertAlmostEqual(parts["breadth"].iloc[-1], 15 / 25)
        self.assertEqual(parts["members"].iloc[-1], 25)

    def test_breadth_uses_the_days_members_and_needs_twenty(self):
        index = pd.bdate_range("2024-01-01", periods=80)
        frames = {f"S{i}.IS": frame(pd.Series(np.linspace(100, 150, 80), index=index)) for i in range(25)}
        eligible = pd.DataFrame(True, index=index, columns=list(frames))
        eligible.iloc[-1, :6] = False  # 19 members on the last day
        parts = R.components(pd.Series(100.0, index=index), frames, eligible)
        self.assertTrue(np.isnan(parts["breadth"].iloc[-1]))
        self.assertEqual(parts["breadth"].iloc[-2], 1.0)

    def test_no_look_ahead(self):
        rng = np.random.default_rng(1)
        close = series(100 * np.exp(np.cumsum(rng.normal(0, 0.015, 600))))
        index = close.index
        frames = {f"S{i}.IS": frame(pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.02, 600))), index=index))
                  for i in range(22)}
        cut = 520
        before = R.labels(close.iloc[:cut], {s: df.iloc[:cut] for s, df in frames.items()}, None)
        changed = close.copy()
        changed.iloc[cut:] *= 3
        after = R.labels(changed, {s: df * np.r_[np.ones(cut), np.full(600 - cut, 0.2)][:, None]
                                   for s, df in frames.items()}, None)
        pd.testing.assert_series_equal(after.iloc[:cut], before)
        self.assertIn(before.iloc[-1], R.LABELS)


class SectorTest(unittest.TestCase):
    def test_relative_strength_by_hand(self):
        bench = series([100, 100, 100, 100, 100, 110] + [110] * 15)
        sector = series([50, 50, 50, 50, 50, 50] + [50] * 15)
        rs = R.relative_strength(sector, bench, 20)
        self.assertAlmostEqual(rs, (50 / 50 - 1) * 100 - (110 / 100 - 1) * 100)  # −10 points
        self.assertIsNone(R.relative_strength(series([1.0, 2.0]), bench, 20))  # too short


class TextTest(unittest.TestCase):
    def test_market_text(self):
        rng = np.random.default_rng(2)
        index = pd.bdate_range("2024-01-01", periods=600)
        bench = frame(pd.Series(100 * np.exp(np.cumsum(rng.normal(0.001, 0.01, 600))), index=index))
        frames = {f"S{i}.IS": frame(pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.02, 600))), index=index))
                  for i in range(30)}
        sectors = {"XBANK.IS": frame(pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.02, 600))), index=index))}
        text = R.market_text(bench, frames, sectors, day=date(2026, 10, 28))
        self.assertIn("Rejim:", text)
        self.assertIn("Genişlik:", text)
        self.assertIn("Banka", text)
        self.assertIn("Sınai: veri yok", text)
        self.assertIn("Rejim bir etikettir, sinyal değildir", text)
        self.assertIn("Kural çıktısıdır, öneri değildir.", text)
        lowered = text.lower()
        for word in (" al ", " sat ", "alım zamanı", "fırsat", "güvenilir"):
            self.assertNotIn(word, lowered)

    def test_without_data(self):
        text = R.market_text(pd.DataFrame(), {}, {}, day=date(2026, 10, 28))
        self.assertIn("bilinmiyor", text)


class BotTest(unittest.TestCase):
    def test_registered(self):
        from bot.handlers import COMMANDS, MENU
        from bot.start import HELP_TEXT

        self.assertIn("piyasa", dict(COMMANDS))
        self.assertIn("piyasa", dict(MENU))
        self.assertIn("/piyasa", HELP_TEXT)

    def test_command_reads_the_store(self):
        import asyncio
        from types import SimpleNamespace
        from unittest import mock

        from bot import analysis
        from tests.test_screen_telegram import fake_update

        rng = np.random.default_rng(3)
        index = pd.bdate_range("2024-01-01", periods=400)

        def bars(symbol):
            return frame(pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.01, 400))), index=index))

        sent = []
        with mock.patch("core.reports.daily.adjusted_bars", side_effect=bars):
            asyncio.run(analysis.market_cmd(fake_update(sent), SimpleNamespace(args=[])))
        self.assertIn("🌐 Piyasa", sent[0][0])
        self.assertIn("Banka:", sent[0][0])
        self.assertNotIn("Banka: veri yok", sent[0][0])

    def test_today_label(self):
        from unittest import mock

        rng = np.random.default_rng(4)
        index = pd.bdate_range("2024-01-01", periods=400)

        def bars(symbol):
            return frame(pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.01, 400))), index=index))

        with mock.patch("core.reports.daily.adjusted_bars", side_effect=bars):
            self.assertIn(R.today_label(), R.LABELS)
        with mock.patch("core.reports.daily.adjusted_bars", return_value=pd.DataFrame()):
            self.assertEqual(R.today_label(), "bilinmiyor")

    def test_sector_indices_are_updated(self):
        from core.reports import daily

        wanted = daily.symbols_to_update(universe=[])
        for code in R.SECTORS:
            self.assertIn(code, wanted)


if __name__ == "__main__":
    unittest.main()
