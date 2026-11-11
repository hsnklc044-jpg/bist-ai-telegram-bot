"""/karne HİSSE with the professional score (D and I madde 3, the user's 11.11.2026 decision). Written before the code.

Title and date; the professional score and class, then the user's scorecard total under it; six 10-box bars (one per
dimension); price, support and resistance with the distance to the close; "Geçmiş": the days in the research period
(before the holdout) when the stock was in the same class, and what happened 20 sessions later (stock, XU100, share
that rose); fewer than 30 days: "Geçmiş örnek az". No look-ahead: a day counts only if its 20 sessions are inside the
data. "/karne HİSSE detay" shows each dimension's criteria and the script's 12 indicators."""

import re
import unittest
from datetime import date

import numpy as np
import pandas as pd

from core.analytics import pro_card as C
from core.analytics import pro_score as P
from core.reports import style


def full(points: int) -> P.ProScore:
    parts, left = {}, points
    for d in P.DIMENSIONS:
        take = min(d.maximum, left)
        parts[d.name] = take
        left -= take
    return P.ProScore(parts=parts)


class BarTest(unittest.TestCase):
    def test_ten_boxes_each_ten_percent(self):
        self.assertEqual(C.bar(20, 20), "██████████")
        self.assertEqual(C.bar(10, 20), "█████░░░░░")
        self.assertEqual(C.bar(7, 15), "█████░░░░░")  # 46,7 % -> 5 boxes
        self.assertEqual(C.bar(0, 10), "░░░░░░░░░░")


class TextTest(unittest.TestCase):
    def setUp(self):
        past = C.Past("Olumlu", 60, 79, 45, 0.012, 0.008, 0.56)
        self.text = C.text("THYAO.IS", date(2026, 11, 10), full(70), 65, close=312.5, support=310.0,
                           resistance=320.0, past=past)
        self.lines = self.text.splitlines()

    def test_title_scores_and_bars(self):
        self.assertEqual(self.lines[0], "THYAO · TEKNİK KARNE · 10.11.2026")
        self.assertEqual(self.lines[1], "🟢 70/100 · Olumlu")
        self.assertEqual(self.lines[2], "Betik karnesi: 65/100")
        bars = re.findall(r"<pre>(.*?)</pre>", self.text, flags=re.S)
        rows = bars[0].splitlines()
        self.assertEqual(len(rows), 6)
        self.assertTrue(rows[0].startswith("Uzun trend"))
        self.assertIn("██████████ 20/20", rows[0])
        self.assertTrue(all(len(r) <= style.TABLE_WIDTH for block in bars for r in block.splitlines()))

    def test_price_support_resistance_with_distance(self):
        block = re.findall(r"<pre>(.*?)</pre>", self.text, flags=re.S)[1]
        self.assertIn("312,50", block)
        self.assertIn("310,00", block)
        self.assertIn("-0,8%", block)
        self.assertIn("+2,4%", block)

    def test_the_past_lines(self):
        self.assertIn("Geçmiş · Olumlu 60–79 puan · 20 gün", self.lines)
        self.assertIn("Ort. +1,2% · XU100 +0,8% · İsabet 56%", self.lines)
        few = C.text("THYAO.IS", date(2026, 11, 10), full(70), 65, 312.5, 310.0, 320.0,
                     C.Past("Olumlu", 60, 79, 12, 0.0, 0.0, 0.5))
        self.assertIn("Geçmiş örnek az", few)

    def test_style_and_the_detail_hint(self):
        self.assertEqual(self.lines[-1], "Ayrıntı: /karne THYAO detay")
        self.assertEqual(style.forbidden(self.text), [])

    def test_a_missing_dimension_is_shown_and_uncoloured(self):
        s = full(70)
        s.parts["Göreli güç"] = None
        text = C.text("THYAO.IS", date(2026, 11, 10), s, 65, 312.5, None, None, None)
        self.assertIn("eksik boyut: Göreli güç", text.splitlines()[1])
        self.assertNotIn("🟢", text.splitlines()[1])
        self.assertIn("veri yok", text)


class PastTest(unittest.TestCase):
    def test_same_class_days_twenty_sessions_later_without_look_ahead(self):
        days = pd.bdate_range("2024-01-01", periods=100)
        totals = pd.Series([70.0] * 100, index=days)
        totals.iloc[80:] = 30.0  # the last 20 days are another class
        close = pd.Series(100 * 1.001 ** np.arange(100), index=days)
        bench = pd.Series(100.0, index=days)
        got = C.past(totals, close, bench, current=70)
        self.assertEqual((got.label, got.low, got.high), ("Olumlu", 60, 79))
        self.assertEqual(got.days, 80)  # days 0..79, each with 20 sessions inside the data
        self.assertAlmostEqual(got.mean, 1.001 ** 20 - 1, places=6)
        self.assertEqual(got.bench_mean, 0.0)
        self.assertEqual(got.hit, 1.0)

    def test_a_day_whose_twenty_sessions_are_not_in_the_data_never_counts(self):
        days = pd.bdate_range("2024-01-01", periods=30)
        totals = pd.Series(70.0, index=days)
        close = pd.Series(100.0, index=days)
        got = C.past(totals, close, close, current=70)
        self.assertEqual(got.days, 10)

    def test_missing_scores_are_not_a_class(self):
        days = pd.bdate_range("2024-01-01", periods=60)
        totals = pd.Series(np.nan, index=days)
        got = C.past(totals, pd.Series(1.0, index=days), pd.Series(1.0, index=days), current=70)
        self.assertEqual(got.days, 0)


class FrameTest(unittest.TestCase):
    def test_the_vectorised_totals_equal_the_row_score(self):
        rows = pd.DataFrame([
            {"close": 110.0, "sma(200)": 100.0, "sma(50)": 105.0, "getiri_12a_1a_haric": 20.0,
             "getiri_6a_1a_haric": -5.0, "goreli_guc_yuzdelik": 45.0, "zirve_uzaklik": -12.0, "macd": 1.0,
             "macd_sinyal": 0.5, "rsi": 72.0, "ema20": 108.0, "obv_egim": 0.3, "cmf": -5.0, "oynaklik_sira": 50.0},
            {"close": 90.0, "sma(200)": 100.0, "sma(50)": np.nan, "getiri_12a_1a_haric": -1.0,
             "getiri_6a_1a_haric": 5.0, "goreli_guc_yuzdelik": 75.0, "zirve_uzaklik": -3.0, "macd": 0.1,
             "macd_sinyal": 0.5, "rsi": 55.0, "ema20": 95.0, "obv_egim": -0.3, "cmf": 5.0, "oynaklik_sira": 95.0},
        ])
        vector = P.totals(rows)
        self.assertEqual(vector.iloc[0], P.score(rows.iloc[0]).total)
        self.assertTrue(np.isnan(vector.iloc[1]))  # a missing dimension: no total for the past classes


class CommandTest(unittest.TestCase):
    def test_karne_default_and_detail(self):
        import inspect

        from bot import analysis

        source = inspect.getsource(analysis._scorecard_text)
        self.assertIn("pro_card.text(", source)
        self.assertIn("pro_card.detail(", source)


if __name__ == "__main__":
    unittest.main()
