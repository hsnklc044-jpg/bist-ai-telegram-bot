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
