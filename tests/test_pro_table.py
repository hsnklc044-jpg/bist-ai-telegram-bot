"""/tablo with the professional score (C, the user's 11.11.2026 decision). Written before the code.

TEKNİK TABLO · date, then "N hisse · Ort. puan X · sınıf", then a <pre> table (colour, stock, score, support,
resistance; score ≥ 40, best first, at most 6 rows, right aligned, ≤ 32 characters), then the weak counts and the
candle notes only when there are any. "/tablo ... detay" keeps the per-stock indicators. Relative strength is ranked
in the BIST 100, not among the listed stocks. The scores and rules themselves do not change."""

import re
import unittest
from datetime import date

from core.analytics import pro_score as P
from core.analytics import symbol_table as T
from core.reports import style

DAY = date(2026, 11, 10)


def ps(total_parts: dict, warning=False):
    s = P.ProScore(parts=dict(total_parts), warning=warning)
    return s


def full(points: int):
    """A ProScore with the given total spread over the six dimensions."""

    parts, left = {}, points
    for d in P.DIMENSIONS:
        take = min(d.maximum, left)
        parts[d.name] = take
        left -= take
    return ps(parts)


def rows():
    return [
        T.ProRow("THYAO.IS", full(82), 289.76, 305.40, "", DAY),
        T.ProRow("GARAN.IS", full(65), 112.5, 118.0, "Yutan Boğa", DAY),
        T.ProRow("ASELS.IS", full(45), 150.0, None, "", DAY),
        T.ProRow("BIMAS.IS", full(30), 500.0, 520.0, "Yutan Ayı", DAY),
        T.ProRow("SISE.IS", full(10), 40.0, 42.0, "Düşüş Marubozu", DAY),
        T.ProRow("KCHOL.IS", ps({**full(70).parts, "Göreli güç": None}), 180.0, 190.0, "", DAY),
        T.ProRow("AKBNK.IS", full(50), 60.0, 62.0, "", DAY),
        T.ProRow("TUPRS.IS", full(55), 1650.0, 1720.0, "", DAY),
        T.ProRow("FROTO.IS", full(61), 950.0, 1010.0, "", DAY),
        T.ProRow("EREGL.IS", full(41), 30.0, 31.0, "", DAY),
    ]


class TextTest(unittest.TestCase):
    def setUp(self):
        self.text = T.pro_text("bist100_trend", rows())
        self.lines = self.text.splitlines()

    def test_title_and_summary_line(self):
        self.assertEqual(self.lines[0], "TEKNİK TABLO · 10.11.2026")
        # 9 stocks with a full score: mean of 82 65 45 30 10 50 55 61 41 = 48,8 -> Karışık
        self.assertEqual(self.lines[1], "10 hisse · Ort. puan 49 · 🟡 Karışık")

    def test_the_table_best_first_at_most_six_score_40_and_over(self):
        table = re.search(r"<pre>(.*?)</pre>", self.text, flags=re.S).group(1).splitlines()
        codes = [line.split()[1] for line in table[1:]]
        self.assertEqual(codes, ["THYAO", "GARAN", "FROTO", "TUPRS", "AKBNK", "ASELS"])
        self.assertTrue(all(len(line) <= style.TABLE_WIDTH for line in table), table)
        self.assertIn("289,76", table[1])
        self.assertIn("1.720", table[4])  # 1.000 TL and over without decimals
        self.assertTrue(table[6].rstrip().endswith("—"))  # no resistance found

    def test_weak_counts_and_candle_notes_only_when_there_are_any(self):
        self.assertIn("Zayıf 1 · Çok zayıf 1 · Veri eksik 1", self.lines)
        self.assertIn("Uyarı: BIMAS, SISE düşüş mumu", self.lines)
        self.assertIn("Not: GARAN yükseliş mumu", self.lines)
        quiet = T.pro_text("x", [T.ProRow("THYAO.IS", full(82), 1.0, 2.0, "", DAY)])
        self.assertNotIn("Zayıf", quiet)
        self.assertNotIn("Uyarı:", quiet)
        self.assertNotIn("Not:", quiet)

    def test_the_detail_command_is_named_and_the_style_holds(self):
        self.assertEqual(self.lines[-1], "Ayrıntı: /tablo bist100_trend detay")
        self.assertEqual(style.forbidden(self.text), [])
        self.assertEqual([p for p in style.problems(self.text, "tablo") if "emoji" in p or "tablo" in p], [])

    def test_nothing_at_40_or_over(self):
        text = T.pro_text("x", [T.ProRow("SISE.IS", full(10), 40.0, 42.0, "", DAY)])
        self.assertIn("Puanı 40 ve üstü hisse yok", text)
        self.assertNotIn("<pre>", text)


class RankingTest(unittest.TestCase):
    def test_relative_strength_is_ranked_in_the_universe_not_the_list(self):
        import numpy as np
        import pandas as pd

        days = pd.bdate_range("2025-01-01", periods=320)

        def frame(drift):
            close = pd.Series(100 * np.exp(drift * np.arange(320)), index=days)
            return pd.DataFrame({"open": close, "high": close, "low": close, "close": close, "volume": 1000.0})

        universe = {f"U{i}.IS": frame(0.004 - 0.0004 * i) for i in range(10)}  # U0 strongest
        weak = {"LIST.IS": universe["U8.IS"]}
        alone = P.latest(weak, universe["U5.IS"]["close"])
        ranked = P.latest(weak, universe["U5.IS"]["close"], universe=universe)
        self.assertEqual(alone["LIST.IS"].parts["Göreli güç"], 20)  # alone it is the top of a one-stock list
        self.assertEqual(ranked["LIST.IS"].parts["Göreli güç"], 0)  # in the universe it is near the bottom


class CommandTest(unittest.TestCase):
    def test_detay_keeps_the_indicator_lines(self):
        import inspect

        from bot import analysis

        source = inspect.getsource(analysis._table_text)
        self.assertIn('"detay"', source)
        self.assertIn("T.pro_text(", source)
        self.assertIn("T.text(", source)


if __name__ == "__main__":
    unittest.main()
