"""
Fixes for the YÜKSEK findings of the independent validation (docs/validation/M31.md, M32.md; v0.99.52):
- M32-1: several cards on one day could each take the same free cash; a button now re-checks it;
- M32-2: panic erased an open position's loss; it now closes it at the last close and counts it;
- M31-1: a model that failed its test still titled its card "✅ AI onayı".
"""

import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import pandas as pd

from core.signals import panic
from core.signals import store as S

DAY = date(2026, 11, 3)


class Book(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.book = self.dir / "signals.db"
        patcher = mock.patch.object(panic, "PANIC_FILE", self.dir / "panic.lock")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.conn = S.connect(self.book)
        self.addCleanup(self.conn.close)


class CashTest(Book):
    def card(self, symbol, qty=200, price=250.0):
        return S.add(self.conn, DAY, symbol, price, 0.7, source="tara-ai", qty=qty, status=S.PENDING)

    def test_the_box_is_never_exceeded(self):
        # each card was sized on the full box: 200 lots × 250 TL = 50.000 TL
        a, b, c = self.card("A.IS"), self.card("B.IS"), self.card("C.IS")
        self.assertEqual(S.decide(self.conn, a, True, DAY), "bekliyor")
        self.assertEqual(S.decide(self.conn, b, True, DAY), "bekliyor")
        self.assertEqual(S.decide(self.conn, c, True, DAY), "nakit_yok")  # 100.000 TL is used
        box, free = S.cash(self.conn)
        self.assertGreaterEqual(free, 0)
        self.assertEqual({s.symbol: s.status for s in S.signals(self.conn)}["C.IS"], S.PENDING)  # still undecided

    def test_lots_shrink_to_the_free_cash(self):
        a = self.card("A.IS", qty=300)  # 75.000 TL
        b = self.card("B.IS", qty=200)  # wants 50.000 TL, 25.000 TL is free
        S.decide(self.conn, a, True, DAY)
        self.assertEqual(S.decide(self.conn, b, True, DAY), "bekliyor")
        self.assertEqual({s.symbol: s.qty for s in S.signals(self.conn)}["B.IS"], 100)


def bars(closes):
    idx = pd.bdate_range("2026-11-02", periods=len(closes))
    return pd.DataFrame({"open": closes, "high": closes, "low": closes, "close": closes}, index=idx)


class PanicTest(Book):
    def test_an_open_loss_is_counted_not_erased(self):
        S.add(self.conn, date(2026, 11, 2), "A.IS", 100.0, qty=100)
        S.add(self.conn, date(2026, 11, 2), "B.IS", 100.0, qty=100)  # stays waiting (no candle)
        S.update(self.conn, lambda s: bars([100.0, 100.0]) if s == "A.IS" else None)
        n = panic.trigger(DAY, book=self.book, bars=lambda s: bars([100.0, 100.0, 93.0]) if s == "A.IS" else None)
        self.assertEqual(n, 2)
        states = {s.symbol: s for s in S.signals(self.conn)}
        self.assertEqual(states["B.IS"].status, "iptal")
        a = states["A.IS"]
        self.assertEqual((a.status, a.exit_price), ("panik", 93.0))
        self.assertAlmostEqual(a.r, 0.93 - 1 - S.COST)
        box, _ = S.cash(self.conn)
        self.assertAlmostEqual(box, S.CAPITAL + 100 * 100.0 * (0.93 - 1 - S.COST))  # the loss stays in the box

    def test_no_price_keeps_the_position_open(self):
        S.add(self.conn, date(2026, 11, 2), "A.IS", 100.0, qty=100)
        S.update(self.conn, lambda s: bars([100.0, 100.0]))
        panic.trigger(DAY, book=self.book, bars=lambda s: None)
        self.assertEqual(S.signals(self.conn)[0].status, "acik")  # not erased, not invented


class CardTitleTest(unittest.TestCase):
    def test_a_failed_model_does_not_say_approved(self):
        from core.screen import ai

        c = ai.Candidate("THYAO.IS", 250.0, 31.2, 14.0, 0.05, -0.4, 0.64)
        text = ai.message(c, validated=False)
        self.assertNotIn("AI onayı", text)
        self.assertIn("Doğrulanmamış model sinyali: THYAO", text)
        self.assertIn("✅ <b>AI onayı: THYAO", ai.message(c, validated=True))


class MediumFindingsTest(unittest.TestCase):
    """ORTA/DÜŞÜK findings (M32-5, M32-6, M31-ORTA-4), v0.99.53. M32-7 (the 9,5% limit as a float) is
    shared by ten modules and the research labels: changed together or not at all (AUDIT)."""

    def signal(self):
        return S.Signal(1, date(2026, 11, 2), "A.IS", "bekliyor", None, None, None, None, None, None, None, None)

    def frame(self, rows):
        idx = pd.bdate_range("2026-11-02", periods=len(rows))
        return pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx)

    def test_a_zero_price_candle_is_bad_data_not_a_total_loss(self):
        df = self.frame([(100, 100, 100, 100), (100, 101, 99.5, 100), (0, 0, 0, 0), (100, 101, 99.5, 100.5)])
        got = S._follow(self.signal(), df)
        self.assertNotEqual(got.get("status"), "stop")  # it used to close at 0: r = −100,15%
        self.assertEqual(got["status"], "acik")

    def test_a_nan_close_does_not_end_without_a_result(self):
        rows = [(100, 100, 100, 100)] + [(100, 101, 99.5, 100)] * 9 + [(100, 101, 99.5, float("nan"))]
        got = S._follow(self.signal(), self.frame(rows))
        if got.get("status") == "sure":
            self.assertFalse(pd.isna(got["r"]))  # never NULL in the box

    def test_card_line_with_no_events(self):
        from core.analytics import card_study as C

        empty = C.Result(0, 0, None, None, None, (float("nan"), float("nan")), None, None, None, False, "olay yok")
        self.assertIn("olay yok", C.card_line(empty, "x"))


class StaleDataTest(Book):
    """M31-ORTA-3: with stale prices a card was still dated today (last candle 14.07 → card 04.11)."""

    def test_no_card_from_an_old_candle(self):
        from core.screen import ai

        c = ai.Candidate("THYAO.IS", 250.0, 31.2, 14.0, 0.05, -0.4, 0.7, candle_day=date(2026, 7, 14))
        with mock.patch.object(ai, "candidates", return_value=[c]):
            out = ai.run(date(2026, 11, 4), {}, object(), validated=False, book=self.book,
                         expected=date(2026, 11, 3))
        self.assertEqual([card for _, card in out], [None, None])  # no buttons, nothing written
        self.assertIn("veri eski", out[1][0])
        self.assertIn("14.07.2026", out[1][0])
        self.assertEqual(S.signals(self.conn), [])

    def test_a_current_candle_still_makes_a_card(self):
        from core.screen import ai

        c = ai.Candidate("THYAO.IS", 250.0, 31.2, 14.0, 0.05, -0.4, 0.7, candle_day=date(2026, 11, 3))
        with mock.patch.object(ai, "candidates", return_value=[c]):
            out = ai.run(date(2026, 11, 4), {}, object(), validated=False, book=self.book,
                         expected=date(2026, 11, 3))
        self.assertIsNotNone(out[1][1])


class ScenarioInputTest(unittest.TestCase):
    """M27 ORTA 2 and 3 (docs/validation/M27.md), v0.99.57."""

    def test_zero_or_negative_levels_are_refused_not_a_crash(self):
        from core.analytics import scenarios

        df = pd.DataFrame({"close": [10.0] * 30, "volume": [1e6] * 30},
                          index=pd.bdate_range("2026-09-01", periods=30))
        text = scenarios.custom_text("X.IS", df, 0.0, -5.0, 10.0, account=100_000)
        self.assertIn("sıfırdan büyük", text)

    def test_turkish_thousands_separator(self):
        from core.analytics.scenarios import _number

        self.assertEqual(_number("1.250"), 1250.0)
        self.assertEqual(_number("12.500"), 12500.0)
        self.assertEqual(_number("1.250,5"), 1250.5)
        self.assertEqual(_number("240,5"), 240.5)
        self.assertEqual(_number("240.5"), 240.5)  # one or two decimals: a decimal point
        self.assertEqual(_number("240"), 240.0)


class HonestLabelsTest(unittest.TestCase):
    """M1 and M8 YÜKSEK (docs/validation/M1.md, M8.md), v0.99.62: unmeasured power is not shown as power."""

    def test_top_list_says_first_that_the_score_has_no_power(self):
        from bot.analysis import _format_signals

        text = _format_signals([{"symbol": "AAA", "signal": "STRONG BUY", "score": 85, "trend": "yukarı"}])
        lines = text.splitlines()
        self.assertNotIn("en güçlü", text)
        self.assertIn("Teknik skoru en yüksek", lines[0])
        self.assertIn("tahmin gücü", lines[1])  # before the list, not after it

    def test_level_strength_is_marked_unmeasured(self):
        from core.analytics import levels as L

        lv = L.Level(price=100.0, kind="destek", method="küme", name="", dist_atr=-0.5, dist_pct=-1.0,
                     strength=72, touches=3, breaks=0, last_touch=None)
        self.assertIn("güç 72 (ölçülmemiş puan", L._line(lv))
