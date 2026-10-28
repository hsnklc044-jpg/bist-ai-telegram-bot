"""
Özellik Talimatı A (DECISIONS K-49): support and resistance levels from closed, adjusted daily
candles. Every number here can be checked by hand; the levels of a day never change when the
future changes (no look-ahead).
"""

import math
import unittest
from datetime import date

import numpy as np
import pandas as pd

from core.analytics import levels as L


def candles(highs, lows=None, closes=None, start="2026-01-05"):
    index = pd.bdate_range(start, periods=len(highs))
    highs = np.asarray(highs, dtype=float)
    lows = highs - 2 if lows is None else np.asarray(lows, dtype=float)
    closes = (highs + lows) / 2 if closes is None else np.asarray(closes, dtype=float)
    return pd.DataFrame({"open": closes, "high": highs, "low": lows, "close": closes, "volume": 1e6}, index=index)


class FractalTest(unittest.TestCase):
    def test_a_peak_is_known_only_n_sessions_later(self):
        highs = [100, 101, 102, 103, 104, 108, 104, 103, 102, 101, 100, 100]
        df = candles(highs)
        self.assertEqual(L.pivots(df.iloc[:10], n=5), [p for p in L.pivots(df.iloc[:10], n=5) if p.kind == "dip"])
        tops = [p for p in L.pivots(df.iloc[:11], n=5) if p.kind == "tepe"]
        self.assertEqual([(p.day, p.price) for p in tops], [(df.index[5], 108.0)])

    def test_equal_highs_on_the_right_still_make_one_peak(self):
        df = candles([100, 101, 102, 103, 104, 108, 108, 103, 102, 101, 100, 99])
        tops = [p for p in L.pivots(df, n=5) if p.kind == "tepe"]
        self.assertEqual([p.day for p in tops], [df.index[5]])  # strictly above the left, at least the right

    def test_limit_days_make_no_pivot(self):
        closes = [100.0] * 5 + [111.0] + [100.0] * 6  # +11% then back: a locked day, not a free top
        df = candles([c + 1 for c in closes], [c - 1 for c in closes], closes)
        self.assertEqual([p for p in L.pivots(df, n=5) if p.kind == "tepe"], [])


class ClusterTest(unittest.TestCase):
    def test_points_closer_than_half_an_atr_merge(self):
        points = [L.Pivot(pd.Timestamp("2026-01-05"), 100.0, "tepe"), L.Pivot(pd.Timestamp("2026-02-05"), 100.8, "dip"),
                  L.Pivot(pd.Timestamp("2026-03-05"), 101.6, "tepe"), L.Pivot(pd.Timestamp("2026-04-06"), 110.0, "tepe")]
        groups = L.cluster(points, width=1.0)  # 0.5 ATR with ATR 2
        self.assertEqual([len(g) for g in groups], [3, 1])
        self.assertAlmostEqual(np.mean([p.price for p in groups[0]]), 100.8)

    def test_breaks_count_side_changes_beyond_half_an_atr(self):
        close = pd.Series([95, 99.6, 101, 104, 99, 96, 100.4, 106], index=pd.bdate_range("2026-01-05", periods=8),
                          dtype=float)
        atr = pd.Series(4.0, index=close.index)  # 0.5 ATR = 2
        self.assertEqual(L.count_breaks(close, 100.0, atr), 3)  # below -> above (104) -> below (96) -> above (106)


class FormulaTest(unittest.TestCase):
    def test_classic_pivots(self):
        p = L.classic(high=110.0, low=90.0, close=105.0)
        self.assertAlmostEqual(p["P"], 305 / 3)
        self.assertAlmostEqual(p["R1"], 2 * 305 / 3 - 90)
        self.assertAlmostEqual(p["D1"], 2 * 305 / 3 - 110)
        self.assertAlmostEqual(p["R2"], 305 / 3 + 20)
        self.assertAlmostEqual(p["D2"], 305 / 3 - 20)

    def test_round_numbers(self):
        self.assertEqual(L.round_numbers(270.0), (250.0, 300.0))
        self.assertEqual(L.round_numbers(27.0), (25.0, 30.0))
        self.assertEqual(L.round_numbers(2.7), (2.5, 3.0))
        self.assertEqual(L.round_numbers(250.0), (250.0, 300.0))

    def test_strength(self):
        self.assertEqual(L.strength(touches=2, age=0, breaks=0), round(100 * (1 - math.exp(-1))))
        self.assertEqual(L.strength(touches=2, age=252, breaks=1), round(100 * (1 - math.exp(-1)) * math.exp(-1) * 0.5))
        self.assertEqual(L.strength(touches=1, age=0, breaks=0), round(100 * (1 - math.exp(-0.5))))


def market(n=400, seed=3):
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.015, n)))
    index = pd.bdate_range("2024-06-03", periods=n)
    high, low = close * (1 + rng.uniform(0, 0.02, n)), close * (1 - rng.uniform(0, 0.02, n))
    return pd.DataFrame({"open": close, "high": high, "low": low, "close": close, "volume": 1e6}, index=index)


class LevelsTest(unittest.TestCase):
    def test_kinds_distances_and_names(self):
        df = market()
        found = L.levels(df)
        last, atr = df["close"].iloc[-1], L.atr(df).iloc[-1]
        self.assertTrue(found)
        for level in found:
            with self.subTest(level=level):
                self.assertEqual(level.kind, "destek" if level.price < last else "direnç")
                self.assertAlmostEqual(level.dist_atr, (level.price - last) / atr)
                self.assertAlmostEqual(level.dist_pct, (level.price / last - 1) * 100)
                self.assertIn(level.method, L.METHODS)
        methods = {lv.method for lv in found}
        self.assertTrue({"küme", "pivot_gün", "pivot_hafta", "52h_zirve", "52h_dip", "psikolojik", "sma50", "sma200"}
                        <= methods)
        clusters = [lv for lv in found if lv.method == "küme"]
        self.assertTrue(all(0 <= lv.strength <= 100 and lv.touches >= 1 for lv in clusters))
        self.assertTrue(all(lv.strength is None for lv in found if lv.method != "küme"))

    def test_no_look_ahead(self):
        df = market()
        cut = 300
        before = L.levels(df.iloc[:cut])
        changed = df.copy()
        changed.iloc[cut:, :4] *= np.linspace(0.5, 3.0, len(df) - cut)[:, None]  # rewrite the future
        self.assertEqual(L.levels(changed.iloc[:cut]), before)
        self.assertEqual(L.levels(changed, asof=df.index[cut - 1]), before)

    def test_nearest(self):
        df = market()
        near = L.nearest(L.levels(df), 3)
        self.assertLessEqual(len(near["destek"]), 3)
        self.assertLessEqual(len(near["direnç"]), 3)
        self.assertEqual([lv.price for lv in near["destek"]], sorted((lv.price for lv in near["destek"]), reverse=True))
        self.assertEqual([lv.price for lv in near["direnç"]], sorted(lv.price for lv in near["direnç"]))

    def test_too_short_history(self):
        self.assertEqual(L.levels(market(20)), [])


class TextTest(unittest.TestCase):
    def test_label_and_no_advice_words(self):
        df = market()
        text = L.levels_text("THYAO.IS", df, date(2026, 10, 28))
        self.assertIn("teknik seviye, öneri değil", text)
        lowered = text.lower()
        for word in ("al ", "sat ", "güçlü destek", "alım bölgesi", "öneri:"):
            self.assertNotIn(word, lowered)


class StudyNoteTest(unittest.TestCase):
    """§3.3: the measurement found no difference from random levels (RESEARCH_LOG, 28.10.2026), so
    every level output carries the note."""

    def test_note_everywhere(self):
        self.assertIn("rastgele seviyeden ayırt edilemedi", L.STUDY_NOTE)
        self.assertIn(L.STUDY_NOTE, L.levels_text("THYAO.IS", market()))
        self.assertIn("ayırt edilemedi", L.position_line(market()))


class WebTest(unittest.TestCase):
    def test_route(self):
        from unittest import mock

        from fastapi.testclient import TestClient

        from core.web.app import app

        with mock.patch("core.reports.daily.adjusted_bars", return_value=market()):
            answer = TestClient(app).get("/seviye/THYAO").json()
        self.assertEqual(answer["symbol"], "THYAO")
        self.assertIn("öneri değil", answer["label"])
        self.assertIn("ayırt edilemedi", answer["note"])
        self.assertTrue(answer["levels"])
        self.assertEqual(set(answer["levels"][0]), {"price", "kind", "method", "name", "strength", "touches", "breaks",
                                                    "last_touch", "dist_atr", "dist_pct"})


class BotTest(unittest.TestCase):
    def test_seviye_and_analyze(self):
        import asyncio
        from types import SimpleNamespace
        from unittest import mock

        from bot import analysis
        from bot.handlers import COMMANDS, MENU
        from bot.start import HELP_TEXT
        from tests.test_screen_telegram import fake_update

        self.assertIn("seviye", dict(COMMANDS))
        self.assertIn("seviye", dict(MENU))
        self.assertIn("/seviye", HELP_TEXT)
        sent = []
        with mock.patch("core.reports.daily.adjusted_bars", return_value=market()):
            asyncio.run(analysis.levels_cmd(fake_update(sent), SimpleNamespace(args=["THYAO"])))
        self.assertIn("THYAO seviyeleri", sent[0][0])
        self.assertIn("teknik seviye, öneri değil", sent[0][0])
        sent = []
        asyncio.run(analysis.levels_cmd(fake_update(sent), SimpleNamespace(args=[])))
        self.assertIn("Kullanım", sent[0][0])

        result = {"symbol": "THYAO.IS", "price": 259.0, "signal": "BUY", "score": 20, "trend": "BULLISH",
                  "rsi": 55.0, "macd": 1.0, "volume_ratio": 1.0, "volatility": 0.03, "stop_loss": 243.0,
                  "target_1": 274.0, "target_2": 290.0, "ma20": 250.0, "ma50": 240.0}
        block = L.levels_text("THYAO.IS", market(), k=3)
        text = analysis._format_analysis(result, block)
        self.assertIn("Direnç (yakından uzağa)", text)
        self.assertLessEqual(text.count("· küme ·") + text.count("· pivot"), 6 + 0)
        self.assertIn("2 ATR altı : 243.0", text)  # the view and its ATR lines are unchanged


if __name__ == "__main__":
    unittest.main()
