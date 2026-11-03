"""
Two-way control (03.11.2026 request): /panik and /devam, the panic lock everywhere it must act,
the /durum cash box with live open results, and /tara ai's messages (approval with the stop and
target, the rejection, the not-validated label, nothing written to the book while not validated).
"""

import asyncio
import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np
import pandas as pd

from core.screen import ai
from core.signals import panic
from core.signals import store as S
from tests.test_signal_book import bars


class PanicTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.lock = Path(tmp.name) / "panic.lock"
        self.book = Path(tmp.name) / "signals.db"
        patcher = mock.patch.object(panic, "PANIC_FILE", self.lock)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_panic_cancels_and_locks_until_resume(self):
        conn = S.connect(self.book)
        S.add(conn, date(2026, 11, 2), "A.IS", 100.0)
        S.add(conn, date(2026, 11, 2), "B.IS", 100.0)
        S.update(conn, lambda s: bars([(100, 100, 100, 100), (100, 101, 99, 100)]) if s == "A.IS" else None)
        conn.close()
        self.assertEqual(panic.trigger(date(2026, 11, 3), book=self.book), 2)  # one open, one waiting
        conn = S.connect(self.book)
        self.assertEqual({s.status for s in S.signals(conn)}, {"iptal"})
        with self.assertRaises(S.BreakerTripped):
            S.add(conn, date(2026, 11, 3), "C.IS", 100.0)
        conn.close()
        self.assertTrue(S.locked(date(2026, 11, 3), self.book))
        from core.signals import live

        self.assertEqual(live.track(date(2026, 11, 3), self.book, load=lambda s: None), [])
        self.assertTrue(panic.release())
        self.assertFalse(panic.release())
        self.assertFalse(S.locked(date(2026, 11, 3), self.book))

    def test_bot_commands(self):
        from bot import control, reports
        from tests.test_screen_telegram import fake_update

        sent = []
        with mock.patch("core.config.paths.SIGNALS_DB", self.book), mock.patch.object(panic, "SIGNALS_DB", self.book):
            asyncio.run(control.panic_cmd(fake_update(sent), SimpleNamespace(args=[])))
            asyncio.run(control.panic_cmd(fake_update(sent), SimpleNamespace(args=[])))
            asyncio.run(reports.screen_cmd(fake_update(sent), SimpleNamespace(args=["rsi<30"])))
            asyncio.run(control.resume_cmd(fake_update(sent), SimpleNamespace(args=[])))
        self.assertIn("PANİK: sistem kilitlendi", sent[0][0])
        self.assertIn("zaten açık", sent[1][0])
        self.assertEqual(sent[2][0], reports.PANIC_TEXT)
        self.assertIn("kaldırıldı", sent[3][0])
        from bot.handlers import COMMANDS, MENU
        from bot.start import HELP_TEXT

        for name in ("panik", "devam"):
            self.assertIn(name, dict(COMMANDS))
            self.assertIn(name, dict(MENU))
        self.assertIn("/panik", HELP_TEXT)

    def test_daily_step_stops(self):
        from core.signals import daily as book

        panic.trigger(date(2026, 11, 3), book=self.book)
        text = book.run(date(2026, 11, 3), lambda s: None, None, self.book, enabled=lambda: True)
        self.assertIn("Panik kilidi açık", text)


class CashBoxTest(unittest.TestCase):
    def test_live_open_result_and_balance(self):
        with tempfile.TemporaryDirectory() as tmp:
            conn = S.connect(Path(tmp) / "signals.db")
            S.add(conn, date(2026, 11, 2), "A.IS", 100.0)
            df = bars([(100, 100, 100, 100), (100, 101, 99, 100), (101, 103, 100.5, 102.5)])
            S.update(conn, lambda s: df.iloc[:2])
            text = S.summary(conn, lambda s: df, date(2026, 11, 4))
            conn.close()
        # entry 100 → last 102,50: +2,50% of 10.000 TL = +250 TL open; realized 100.000
        self.assertIn("Sanal kasa: 100.250 TL (%+0,25)", text)
        self.assertIn("açık pozisyonlar 250 TL", text)
        self.assertIn("A: giriş 100,00 → son 102,50 (%+2,50, 250 TL); stop 98,00, hedef 104,00", text)


class AiTest(unittest.TestCase):
    def candidate(self, p):
        return ai.Candidate("THYAO.IS", 250.0, 31.2, 14.0, 0.05, -0.4, p)

    def test_approval_message(self):
        text = ai.message(self.candidate(0.64), validated=False)
        self.assertIn("AI onayı: THYAO", text)
        self.assertIn("ML güven skoru:</b> %64", text)
        self.assertIn("Zarar durdur (%2):</b> ~245,00 TL", text)
        self.assertIn("Kâr al (%4):</b> ~260,00 TL", text)
        self.assertIn("deftere yazılmadı", text)
        self.assertIn("doğrulandı", ai.message(self.candidate(0.64), validated=True))

    def test_rejection_and_threshold(self):
        self.assertIn("AI Reddi</b>: THYAO – olasılık %59", ai.message(self.candidate(0.59), False))
        self.assertIn("AI onayı", ai.message(self.candidate(0.60), False))
        self.assertIn("hesaplanamadı", ai.message(self.candidate(None), False))

    def test_run_writes_the_book_only_when_validated(self):
        class Fixed:
            def predict_proba(self, x):
                return np.array([[0.2, 0.8]])

        rng = np.random.default_rng(0)
        close = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, 400)))
        df = pd.DataFrame({"open": close, "high": close * 1.01, "low": close * 0.99, "close": close,
                           "volume": 1e6}, index=pd.bdate_range("2025-01-01", periods=400))
        with mock.patch("core.market.extended.trigger_mask", side_effect=lambda ind: pd.Series(True, index=ind.index)), \
                tempfile.TemporaryDirectory() as tmp:
            book = Path(tmp) / "signals.db"
            out = ai.run(date(2026, 11, 3), {"A.IS": df}, Fixed(), validated=False, book=book)
            self.assertIn("1 hissede teknik tetik", out[0])
            self.assertIn("AI onayı: A", out[1])
            self.assertFalse(book.exists())  # not validated: nothing recorded
            ai.run(date(2026, 11, 3), {"A.IS": df}, Fixed(), validated=True, book=book)
            conn = S.connect(book)
            self.assertEqual([s.symbol for s in S.signals(conn)], ["A.IS"])
            conn.close()
        self.assertIn("teknik tetik (dip dönüşü) olan hisse yok", ai.run(date(2026, 11, 3), {}, None, False)[0])

    def test_bot_sends_html(self):
        from bot import reports
        from tests.test_screen_telegram import fake_update

        sent = []

        async def reply_text(text, **kw):
            sent.append((text, kw.get("parse_mode")))

        update = fake_update([])
        update.effective_message.reply_text = reply_text
        with mock.patch("core.signals.store.locked", return_value=False), \
                mock.patch("core.screen.ai.live", return_value=["<b>x</b>"]):
            asyncio.run(reports.screen_cmd(update, SimpleNamespace(args=["ai"])))
        self.assertEqual(sent[-1], ("<b>x</b>", "HTML"))


if __name__ == "__main__":
    unittest.main()


class LiveModelTest(unittest.TestCase):
    def test_fit_load_validated_and_live(self):
        from core.ml import signal_filter as SF
        from tests.test_signal_filter import daily

        frames = {f"R{i}.IS": daily(1500, 60 + i) for i in range(30)}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "m.joblib"
            self.assertIsNone(SF.load_live(path))
            rows = SF.fit_live(frames, None, date(2023, 6, 1), path, make=lambda r: SF.fit(r, trees=10))
            self.assertGreater(rows, 0)
            saved = SF.load_live(path)
            self.assertEqual(saved["rows"], rows)
            path.write_bytes(b"bozuk")
            self.assertIsNone(SF.load_live(path))  # a broken file is "no model"
            report = Path(tmp) / "r.json"
            with mock.patch.object(SF, "report_file", return_value=report):
                self.assertFalse(SF.validated())
                report.write_text('{"passed": true}', encoding="utf-8")
                self.assertTrue(SF.validated())
            with mock.patch.object(SF, "load_live", return_value=saved), \
                    mock.patch("core.reports.daily.adjusted_bars", side_effect=lambda s: frames.get("R0.IS")), \
                    mock.patch.object(SF, "validated", return_value=False):
                out = ai.live(date(2026, 11, 3))
        self.assertTrue(out[0].startswith("🔎 /tara ai"))

    def test_weekly_refit_and_panic_since(self):
        from core.reports import daily

        with mock.patch("core.ml.signal_filter._daily", return_value=({}, None)) as data, \
                mock.patch("core.ml.signal_filter.fit_live", return_value=0) as fit:
            daily._refit_signal_model(date(2026, 11, 5))  # Thursday: nothing
            self.assertFalse(fit.called)
            daily._refit_signal_model(date(2026, 11, 6))  # Friday
            self.assertTrue(fit.called and data.called)
        with tempfile.TemporaryDirectory() as tmp:
            lock = Path(tmp) / "panic.lock"
            self.assertIsNone(panic.since(lock))
            panic.trigger(date(2026, 11, 3), lock=lock, book=Path(tmp) / "yok.db")
            self.assertIsNotNone(panic.since(lock))
