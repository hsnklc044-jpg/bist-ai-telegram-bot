"""
Özellik B (DECISIONS K-55): three fixed scenario templates. A calculator, not advice: entry is the
next open, invalidation and target come from fixed rules, R is after costs, the outcome is the
first of invalidation / target / 20 sessions (both on one session: invalidation). Every number
here can be checked by hand.
"""

import math
import unittest

import numpy as np
import pandas as pd

from core.analytics import scenarios as S


def candles(rows, start="2026-01-05"):
    """rows: (open, high, low, close[, volume])"""

    index = pd.bdate_range(start, periods=len(rows))
    data = [r if len(r) == 5 else (*r, 1e6) for r in rows]
    return pd.DataFrame(data, columns=["open", "high", "low", "close", "volume"], index=index, dtype=float)


class RTest(unittest.TestCase):
    def test_r_after_costs_by_hand(self):
        c = S.COST
        self.assertAlmostEqual(c, 0.0015)
        r = S.r_value(entry=100.0, invalidation=95.0, target=110.0)
        self.assertAlmostEqual(r, (110 * (1 - c) - 100 * (1 + c)) / (100 * (1 + c) - 95 * (1 - c)))
        self.assertLess(r, 2.0)  # costs make it smaller than the raw 10/5
        self.assertIsNone(S.r_value(100.0, 101.0, 110.0))  # invalidation not below entry
        self.assertIsNone(S.r_value(100.0, 95.0, 99.0))  # target not above entry

    def test_unfavourable_below_one_and_a_half(self):
        self.assertTrue(S.unfavourable(1.49))
        self.assertFalse(S.unfavourable(1.5))


class OutcomeTest(unittest.TestCase):
    def test_target(self):
        df = candles([(100, 100, 100, 100), (101, 103, 100, 102), (102, 111, 101, 110)])
        out = S.outcome(df, 0, invalidation=95.0, target=110.0)
        self.assertEqual((out.result, out.exit, out.sessions), ("hedef", 110.0, 2))
        self.assertAlmostEqual(out.entry, 101.0)
        c = S.COST
        self.assertAlmostEqual(out.r, (110 * (1 - c) - 101 * (1 + c)) / (101 * (1 + c) - 95 * (1 - c)))

    def test_invalidation_and_gap(self):
        df = candles([(100, 100, 100, 100), (101, 101, 94, 96)])
        self.assertEqual(S.outcome(df, 0, 95.0, 110.0).result, "geçersizlik")
        self.assertEqual(S.outcome(df, 0, 95.0, 110.0).exit, 95.0)
        gap = candles([(100, 100, 100, 100), (101, 102, 100, 101), (90, 92, 89, 91)])
        out = S.outcome(gap, 0, 95.0, 110.0)
        self.assertEqual((out.result, out.exit), ("geçersizlik", 90.0))  # gapped below: the open

    def test_both_on_one_session_counts_as_invalidation(self):
        df = candles([(100, 100, 100, 100), (101, 101, 100, 100), (100, 112, 94, 100)])
        self.assertEqual(S.outcome(df, 0, 95.0, 110.0).result, "geçersizlik")

    def test_time_out_and_pending(self):
        rows = [(100, 100, 100, 100)] + [(101, 102, 100, 101)] * 20
        out = S.outcome(candles(rows), 0, 95.0, 110.0)
        self.assertEqual((out.result, out.sessions, out.exit), ("süre doldu", 20, 101.0))
        self.assertIsNone(S.outcome(candles(rows[:10]), 0, 95.0, 110.0))  # not decided yet
        self.assertIsNone(S.outcome(candles(rows[:1]), 0, 95.0, 110.0))  # no next open yet

    def test_an_open_beyond_the_levels_is_not_filled(self):
        # K-55 addendum (29.10, found on the first real card): a gap past invalidation or target leaves
        # no scenario to enter; it was an undefined R before
        below = candles([(100, 100, 100, 100), (94, 96, 93, 95)])
        above = candles([(100, 100, 100, 100), (106, 107, 105, 106)])
        self.assertEqual(S.outcome(below, 0, 95.0, 110.0).result, "dolmadı")
        self.assertEqual(S.outcome(above, 0, 90.0, 105.0).result, "dolmadı")

    def test_a_limit_open_is_not_filled(self):
        df = candles([(100, 100, 100, 100), (109.6, 110, 109, 110), (110, 120, 109, 115)])
        self.assertEqual(S.outcome(df, 0, 95.0, 112.0).result, "dolmadı")


def walk(n=320, seed=5):
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0.0005, 0.015, n)))
    open_ = np.r_[close[0], close[:-1]] * (1 + rng.normal(0, 0.003, n))
    high = np.maximum(open_, close) * (1 + rng.uniform(0, 0.01, n))
    low = np.minimum(open_, close) * (1 - rng.uniform(0, 0.01, n))
    volume = rng.uniform(0.5e6, 2e6, n)
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume},
                        index=pd.bdate_range("2024-06-03", periods=n))


class TemplateTest(unittest.TestCase):
    def test_rules_hold_on_every_signal(self):
        df = walk()
        table = S.signals(df)
        a = S.levels_atr(df)
        sma20, sma50, sma200 = (df["close"].rolling(n).mean() for n in (20, 50, 200))
        found = 0
        for name in S.TEMPLATES:
            part = table[name]
            for day in part.index[part["ok"]]:
                found += 1
                row, close, atr = part.loc[day], df.at[day, "close"], a.loc[day]
                with self.subTest(template=name, day=day):
                    self.assertLess(row["invalidation"], close)
                    self.assertGreater(row["target"], close)
                    if name == "destek_tepkisi":
                        self.assertLessEqual(close - row["level"], S.NEAR_ATR * atr + 1e-9)
                        self.assertGreaterEqual(row["strength"], S.STRENGTH_MIN)
                        self.assertAlmostEqual(row["invalidation"], row["level"] - atr)
                    if name == "trend_geri_cekilme":
                        self.assertGreater(sma50.loc[day], sma200.loc[day])
                        self.assertLessEqual(abs(close - sma20.loc[day]), S.NEAR_ATR * atr + 1e-9)
                    if name == "direnc_kirilimi":
                        prior = df["volume"].shift(1).rolling(20).mean().loc[day]
                        self.assertGreaterEqual(df.at[day, "volume"], S.VOLUME_X * prior)
                        self.assertAlmostEqual(row["invalidation"], row["level"] - atr)
        self.assertGreater(found, 0)

    def test_no_look_ahead(self):
        df = walk()
        cut = 280
        before = S.signals(df.iloc[:cut])
        changed = df.copy()
        changed.iloc[cut:, :4] *= 1.7
        after = S.signals(changed)
        for name in S.TEMPLATES:
            pd.testing.assert_frame_equal(after[name].iloc[:cut], before[name])


class TextTest(unittest.TestCase):
    def test_scenario_text(self):
        df = walk()
        table = S.signals(df)
        day = next(d for name in S.TEMPLATES for d in table[name].index[table[name]["ok"]])
        text = S.scenario_text("THYAO.IS", df.loc[:day], account=100_000.0)
        self.assertTrue(text.rstrip().endswith(S.DISCLAIMER))
        body = text.replace(S.DISCLAIMER, "").lower()
        for word in (" al ", " sat ", "alım fırsatı", "hedef fiyat önerisi", "kanıtlan"):
            self.assertNotIn(word, body)
        self.assertIn("giriş varsayımı", text)
        self.assertIn("tavan/taban riski", text)
        for name in S.TEMPLATES:
            self.assertIn(S.TITLES[name], text)

    def test_custom_by_hand(self):
        df = walk()
        text = S.custom_text("THYAO.IS", df, entry=240.0, invalidation=232.0, target=262.0, account=100_000.0,
                             risk=0.01)
        r = S.r_value(240.0, 232.0, 262.0)
        self.assertIn(f"R {S.num(r, 2)}", text)
        # 1% of 100.000 TL = 1.000 TL risk; per share 8 TL -> 125 shares, unless liquidity is smaller
        liquidity = float((df["close"] * df["volume"]).shift(1).rolling(20).mean().iloc[-1])
        expected = min(math.floor(1000 / 8), math.floor(liquidity * S.LIQUIDITY_SHARE / 240.0))
        self.assertIn(f"{expected} adet", text)
        self.assertTrue(text.rstrip().endswith(S.DISCLAIMER))

    def test_custom_refuses_impossible_levels(self):
        text = S.custom_text("THYAO.IS", walk(), entry=240.0, invalidation=250.0, target=262.0, account=1e5)
        self.assertIn("geçersizlik girişin altında olmalı", text)


class CommandTest(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(S.parse_args(["THYAO"]), ("THYAO", None, S.DEFAULT_RISK))
        self.assertEqual(S.parse_args(["thyao", "giris", "240", "gecersiz", "232,5", "hedef", "262"]),
                         ("THYAO", (240.0, 232.5, 262.0), S.DEFAULT_RISK))
        self.assertEqual(S.parse_args(["THYAO", "destek", "240", "geçersiz", "232", "hedef", "262", "risk=%0,5"]),
                         ("THYAO", (240.0, 232.0, 262.0), 0.005))
        for bad in ([], ["THYAO", "giris", "240"], ["THYAO", "risk=%9"]):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                S.parse_args(bad)

    def test_bot(self):
        import asyncio
        from types import SimpleNamespace
        from unittest import mock

        from bot import analysis
        from bot.handlers import COMMANDS, MENU
        from bot.start import HELP_TEXT
        from tests.test_screen_telegram import fake_update

        self.assertIn("senaryo", dict(COMMANDS))
        self.assertIn("senaryo", dict(MENU))
        self.assertIn("/senaryo", HELP_TEXT)
        sent = []
        with mock.patch("core.reports.daily.adjusted_bars", return_value=walk()), \
                mock.patch.object(S, "account_value", return_value=100_000.0):
            asyncio.run(analysis.scenario_cmd(fake_update(sent), SimpleNamespace(args=["THYAO"])))
            asyncio.run(analysis.scenario_cmd(fake_update(sent), SimpleNamespace(
                args=["THYAO", "giris", "240", "gecersiz", "232", "hedef", "262"])))
            asyncio.run(analysis.scenario_cmd(fake_update(sent), SimpleNamespace(args=[])))
        self.assertIn("THYAO senaryoları", sent[0][0])
        self.assertIn("senin seviyelerin", sent[1][0])
        self.assertIn("Kullanım", sent[2][0])


if __name__ == "__main__":
    unittest.main()
