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

from core.ml.features import COST
from core.screen import ai
from core.signals import panic
from core.signals import store as S
from tests.test_signal_book import bars


async def _tara_ai(update):
    """/tara ai and the background scan it starts (the handler itself returns at once)."""
    from bot import reports

    await reports.screen_cmd(update, SimpleNamespace(args=["ai"]))
    await asyncio.gather(*reports._BACKGROUND)


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
        self.assertIn("A: giriş 100,00 → son 102,50 (%+2,50, 250 TL)", text)
        # trailing stop: peak 101 (the entry day's high) − 2% = 98,98; at the stop −1,02% of 10.000 TL
        self.assertIn("iz süren stop 98,98 (zirve 101,00 − %2), stopta sonuç -102 TL; kâr al 104,00", text)
        self.assertIn("Dinamik risk", text)


class AiTest(unittest.TestCase):
    def candidate(self, p):
        return ai.Candidate("THYAO.IS", 250.0, 31.2, 14.0, 0.05, -0.4, p)

    def test_approval_message(self):
        text = ai.message(self.candidate(0.64), validated=False)
        self.assertIn("AI onayı: THYAO", text)
        self.assertIn("ML güven skoru:</b> %64", text)
        self.assertIn("Zarar durdur (%2, iz süren):</b> ~245,00 TL", text)
        self.assertIn("Kâr al (%4):</b> ~260,00 TL", text)
        self.assertIn("işleme girmek sizin kararınız", text)
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
            self.assertIn("1 hissede teknik tetik", out[0][0])
            self.assertIn("AI onayı: A", out[1][0])
            self.assertIn("Lot (%1 risk kalkanı)", out[1][0])
            conn = S.connect(book)
            (card,) = S.signals(conn)
            conn.close()
            self.assertEqual((out[1][1], card.status), (card.id, S.PENDING))  # waits for the button
            self.assertEqual(card.qty, S.size_position(S.CAPITAL, S.CAPITAL, float(df["close"].iloc[-1])))
            self.assertEqual(S.signals(S.connect(book), S.OPEN_STATES), [])  # not followed before the button
        self.assertIn("teknik tetik (dip dönüşü) olan hisse yok", ai.run(date(2026, 11, 3), {}, None, False)[0][0])

    def test_bot_sends_html(self):
        from tests.test_screen_telegram import fake_update

        sent = []

        async def reply_text(text, **kw):
            sent.append((text, kw.get("parse_mode")))

        update = fake_update([])
        update.effective_message.reply_text = reply_text
        with mock.patch("core.signals.store.locked", return_value=False), \
                mock.patch("core.screen.ai.live", return_value=[("<b>x</b>", None)]):
            asyncio.run(_tara_ai(update))
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
        self.assertTrue(out[0][0].startswith("🔎 /tara ai"))

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


class ApprovalTest(unittest.TestCase):
    """K-67: the buttons, the 1% risk lots and the trailing stop."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.book = Path(tmp.name) / "signals.db"
        self.lock = Path(tmp.name) / "panic.lock"
        patcher = mock.patch.object(panic, "PANIC_FILE", self.lock)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.conn = S.connect(self.book)
        self.addCleanup(self.conn.close)

    def card(self, day=date(2026, 11, 3), symbol="A.IS", qty=200):
        return S.add(self.conn, day, symbol, 250.0, 0.7, source="tara-ai", qty=qty, status=S.PENDING)

    def test_lots_by_hand(self):
        # 1% of 105.430 TL = 1.054,30 TL; a 2% stop at 250 TL costs 5 TL a lot → 210 lots (52.500 TL)
        self.assertEqual(S.size_position(105_430.0, 105_430.0, 250.0), 210)
        self.assertEqual(S.size_position(105_430.0, 30_000.0, 250.0), 120)  # only what the free cash buys
        self.assertEqual(S.size_position(100_000.0, 0.0, 250.0), 0)
        self.assertEqual(S.size_position(100_000.0, 100_000.0, 0.0), 0)

    def test_cash_counts_open_positions(self):
        self.card(qty=100)
        S.decide(self.conn, 1, True, date(2026, 11, 3))
        box, free = S.cash(self.conn)
        self.assertEqual((box, free), (S.CAPITAL, S.CAPITAL - 100 * 250.0))  # waiting entry: lots × card price

    def test_enter_reject_expire_lock_and_once(self):
        a, b, c, d = (self.card(symbol=s) for s in ("A.IS", "B.IS", "C.IS", "D.IS"))
        today = date(2026, 11, 3)
        self.assertEqual(S.decide(self.conn, a, True, today), "bekliyor")
        self.assertEqual(S.decide(self.conn, a, False, today), "zaten:bekliyor")
        self.assertEqual(S.decide(self.conn, b, False, today), "reddedildi")
        self.assertEqual(S.decide(self.conn, c, True, date(2026, 11, 4)), "zaman_asimi")
        panic.trigger(today, book=self.book)
        self.assertEqual(S.decide(self.conn, d, True, today), "zaten:iptal")  # panic cancelled the waiting card
        with self.assertRaises(S.BreakerTripped):  # no new card while locked
            S.add(self.conn, today, "E.IS", 250.0, 0.7, qty=10, status=S.PENDING)
        panic.release()
        e = S.add(self.conn, today, "E.IS", 250.0, 0.7, qty=10, status=S.PENDING)
        with mock.patch.object(panic, "active", return_value=True):
            self.assertEqual(S.decide(self.conn, e, True, today), "kilitli")  # a button cannot enter while locked
        self.assertEqual(S.decide(self.conn, 999, True, today), "yok")

    def test_trailing_stop_by_hand(self):
        sid = self.card(day=date(2026, 11, 2), qty=100)
        S.decide(self.conn, sid, True, date(2026, 11, 2))
        # entry 100 (03.11 open). The stop before each day: 98 (100 × 0,98), then 103 × 0,98 = 100,94,
        # 103,5 × 0,98 = 101,43, 103,9 × 0,98 = 101,82; the target 104 is never touched. On 06.11 the low 101
        # reaches 101,82: stop at 101,82, a +1,82% gain locked in (before the cost)
        df = bars([(100, 100, 100, 100), (100, 103, 99.5, 102), (102, 103.5, 101.5, 103), (103, 103.9, 103.6, 103.8),
                   (103.8, 103.9, 101, 101.5)])
        S.update(self.conn, lambda s: df)
        s = S.signals(self.conn)[0]
        self.assertEqual(s.status, "stop")
        self.assertAlmostEqual(s.exit_price, 103.9 * 0.98)
        self.assertAlmostEqual(s.r, s.exit_price / 100 - 1 - COST)
        self.assertGreater(s.r, 0)  # the trailing stop locked in a gain

    def test_old_book_is_upgraded(self):
        import sqlite3

        old = Path(self.book.parent) / "old.db"
        raw = sqlite3.connect(old)
        raw.execute("CREATE TABLE signals (id INTEGER PRIMARY KEY AUTOINCREMENT, created TEXT NOT NULL, symbol TEXT "
                    "NOT NULL, signal_close REAL NOT NULL, proba REAL, source TEXT NOT NULL, status TEXT NOT NULL "
                    "DEFAULT 'bekliyor', entry_date TEXT, entry_price REAL, stop REAL, target REAL, exit_date TEXT, "
                    "exit_price REAL, r REAL, UNIQUE (created, symbol))")
        raw.execute("INSERT INTO signals (created, symbol, signal_close, source) VALUES ('2026-11-02', 'A.IS', 1, 'x')")
        raw.commit()
        raw.close()
        conn = S.connect(old)
        self.assertEqual(S.signals(conn)[0].qty, None)
        self.assertEqual(S.signals(conn)[0].notional, S.SIZE)
        conn.close()

    def test_button_callback(self):
        from bot import reports
        from tests.test_screen_telegram import CHAT, fake_update

        sid = self.card()
        got, edits = [], []

        def update_for(data, user=None):
            u = fake_update(got, data=data, user=user)

            async def edit_markup(**kw):
                edits.append(kw)

            u.callback_query.edit_message_reply_markup = edit_markup
            return u

        with mock.patch("bot.reports._allowed_chat", return_value=CHAT), \
                mock.patch("core.signals.store.SIGNALS_DB", self.book), \
                mock.patch("core.config.paths.SIGNALS_DB", self.book), \
                mock.patch("core.market.calendar.now_istanbul",
                           return_value=__import__("datetime").datetime(2026, 11, 3, 15, 0)):
            asyncio.run(reports.signal_button(update_for(f"sinyal:gir:{sid}", user=999), SimpleNamespace()))
            self.assertEqual([t for t, _ in got if t != "<answer>"], [])  # another user: nothing happens
            asyncio.run(reports.signal_button(update_for(f"sinyal:gir:{sid}"), SimpleNamespace()))
            asyncio.run(reports.signal_button(update_for(f"sinyal:iptal:{sid}"), SimpleNamespace()))
            asyncio.run(reports.signal_button(update_for("sinyal:bozuk:x"), SimpleNamespace()))
        texts = [t for t, _ in got if t != "<answer>"]
        self.assertIn("İşleme girildi", texts[0])
        self.assertIn("zaten verilmiş", texts[1])
        self.assertEqual(len(texts), 2)
        self.assertEqual(edits[0], {"reply_markup": None})  # the card lost its buttons

    def test_card_has_buttons(self):
        from tests.test_screen_telegram import fake_update

        sent = []

        async def reply_text(text, **kw):
            sent.append((text, kw.get("reply_markup")))

        update = fake_update([])
        update.effective_message.reply_text = reply_text
        with mock.patch("core.signals.store.locked", return_value=False), \
                mock.patch("core.screen.ai.live", return_value=[("kart", 7), ("ret", None)]):
            asyncio.run(_tara_ai(update))
        buttons = [b.callback_data for row in sent[1][1].inline_keyboard for b in row]
        self.assertEqual(buttons, ["sinyal:gir:7", "sinyal:iptal:7"])
        self.assertIsNone(sent[2][1])



class ResponsivenessTest(unittest.TestCase):
    def test_tara_ai_does_not_block_panik(self):
        # 03.11.2026 22:48: /panik waited behind a /tara ai that was training its model (updates are handled
        # one at a time). /tara ai now returns at once; its work runs in the background.
        import threading

        from bot import control, reports
        from tests.test_screen_telegram import fake_update

        release = threading.Event()
        sent = []

        def slow_live(day):
            release.wait(5)
            return [("bitti", None)]

        async def scenario():
            update = fake_update(sent)
            with mock.patch("core.signals.store.locked", return_value=False), \
                    mock.patch("core.screen.ai.live", side_effect=slow_live), \
                    mock.patch("bot.control.panic_text", return_value="panik işlendi"):
                await asyncio.wait_for(reports.screen_cmd(update, SimpleNamespace(args=["ai"])), 1)
                await asyncio.wait_for(control.panic_cmd(update, SimpleNamespace(args=[])), 1)
                self.assertEqual(sent[-1][0], "panik işlendi")  # before /tara ai finished
                release.set()
                await asyncio.gather(*reports._BACKGROUND)
            self.assertEqual(sent[-1][0], "bitti")

        asyncio.run(scenario())


    def test_second_tara_ai_waits_for_the_first(self):
        import threading

        from bot import reports
        from tests.test_screen_telegram import fake_update

        release = threading.Event()
        sent = []

        def slow_live(day):
            release.wait(5)
            return [("bitti", None)]

        async def scenario():
            update = fake_update(sent)
            with mock.patch("core.signals.store.locked", return_value=False), \
                    mock.patch("core.screen.ai.live", side_effect=slow_live) as live:
                await reports.screen_cmd(update, SimpleNamespace(args=["ai"]))
                await reports.screen_cmd(update, SimpleNamespace(args=["ai"]))
                self.assertEqual(sent[-1][0], reports.AI_BUSY_TEXT)
                release.set()
                await asyncio.gather(*reports._BACKGROUND)
            self.assertEqual(live.call_count, 1)

        asyncio.run(scenario())
