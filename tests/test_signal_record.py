"""
K-70 madde 4: every signal keeps its reason, risk and validity; closed signals are compared with
BIST 100 over the same days, winners and losers measured apart. Every number by hand.
"""

import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import pandas as pd

from core.signals import panic
from core.signals import store as S


class Book(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        patcher = mock.patch.object(panic, "PANIC_FILE", self.dir / "panic.lock")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.conn = S.connect(self.dir / "signals.db")
        self.addCleanup(self.conn.close)


class RecordTest(Book):
    def test_reason_risk_and_validity_are_kept(self):
        sid = S.add(self.conn, date(2026, 11, 4), "A.IS", 250.0, 0.7, source="tara-ai", qty=200, status=S.PENDING,
                    reason="dip dönüşü; RSI 31,2")
        row = self.conn.execute("SELECT * FROM signals WHERE id = ?", (sid,)).fetchone()
        self.assertEqual(row["reason"], "dip dönüşü; RSI 31,2")
        self.assertAlmostEqual(row["risk_tl"], 200 * 250.0 * S.STOP)  # 1.000 TL if the stop hits at the card price
        self.assertEqual(row["valid_until"], "2026-11-04")  # the button is valid on the card's day only
        self.assertEqual(row["horizon"], S.HORIZON)  # then at most this many sessions in the trade

    def test_old_books_get_the_new_columns(self):
        path = self.dir / "old.db"
        old = sqlite3.connect(path)
        old.executescript("CREATE TABLE signals (id INTEGER PRIMARY KEY AUTOINCREMENT, created TEXT NOT NULL, "
                          "symbol TEXT NOT NULL, signal_close REAL NOT NULL, proba REAL, source TEXT NOT NULL, "
                          "status TEXT NOT NULL DEFAULT 'bekliyor', entry_date TEXT, entry_price REAL, stop REAL, "
                          "target REAL, exit_date TEXT, exit_price REAL, r REAL, UNIQUE (created, symbol));")
        old.close()
        conn = S.connect(path)
        have = {r["name"] for r in conn.execute("PRAGMA table_info(signals)")}
        conn.close()
        self.assertTrue({"qty", "peak", "reason", "risk_tl", "valid_until", "horizon", "bench_r"} <= have)


def closed(conn, created, symbol, entry_date, entry, exit_date, exit_price, qty=100):
    sid = S.add(conn, created, symbol, entry, qty=qty)
    r = exit_price / entry - 1 - S.COST
    with conn:
        conn.execute("UPDATE signals SET status = ?, entry_date = ?, entry_price = ?, exit_date = ?, exit_price = ?, "
                     "r = ? WHERE id = ?", ("hedef" if r > 0 else "stop", entry_date.isoformat(), entry,
                                           exit_date.isoformat(), exit_price, r, sid))
    return sid


class PerformanceTest(Book):
    def xu100(self):
        idx = pd.to_datetime(["2026-11-03", "2026-11-04", "2026-11-05", "2026-11-06"])
        return pd.DataFrame({"open": [100.0, 101.0, 102.0, 103.0], "close": [100.5, 101.5, 102.0, 104.0]}, index=idx)

    def test_winners_losers_and_bist100_by_hand(self):
        # A: 100 → 104 (+4% - 0,15% = +3,85%); XU100 from the entry open 101 to the exit close 104: +2,97%
        closed(self.conn, date(2026, 11, 3), "A.IS", date(2026, 11, 4), 100.0, date(2026, 11, 6), 104.0)
        # B: 50 → 49 (−2% − 0,15% = −2,15%); XU100 from 102 (open 05.11) to 102 (close 05.11): 0%
        closed(self.conn, date(2026, 11, 4), "B.IS", date(2026, 11, 5), 50.0, date(2026, 11, 5), 49.0)
        p = S.performance(self.conn, lambda s: self.xu100() if s == S.BENCHMARK else None)
        self.assertEqual((p.closed, p.winners, p.losers), (2, 1, 1))
        self.assertAlmostEqual(p.win_mean, 0.04 - S.COST)
        self.assertAlmostEqual(p.loss_mean, -0.02 - S.COST)
        self.assertAlmostEqual(p.mean, ((0.04 - S.COST) + (-0.02 - S.COST)) / 2)
        self.assertAlmostEqual(p.bench_mean, (104 / 101 - 1 + 0.0) / 2)
        self.assertAlmostEqual(p.excess, p.mean - p.bench_mean)
        # the benchmark result is recorded on the row
        rows = {r["symbol"]: r["bench_r"] for r in self.conn.execute("SELECT symbol, bench_r FROM signals")}
        self.assertAlmostEqual(rows["A.IS"], 104 / 101 - 1)
        self.assertEqual(rows["B.IS"], 0.0)
        text = S.performance_text(p)
        self.assertIn("Kazanan 1 (ort. %+3,85)", text)
        self.assertIn("kaybeden 1 (ort. %-2,15)", text)
        self.assertIn("BIST 100 aynı günlerde ort. %+1,49", text)

    def test_durum_shows_the_performance_line(self):
        closed(self.conn, date(2026, 11, 3), "A.IS", date(2026, 11, 4), 100.0, date(2026, 11, 6), 104.0)
        text = S.summary(self.conn, lambda s: self.xu100() if s == S.BENCHMARK else None, date(2026, 11, 6))
        self.assertIn("📏 Sinyal performansı: 1 kapanmış", text)

    def test_no_closed_signal_says_so(self):
        p = S.performance(self.conn, lambda s: None)
        self.assertEqual(p.closed, 0)
        self.assertIn("kapanmış sinyal yok", S.performance_text(p))

    def test_missing_benchmark_is_not_zero(self):
        closed(self.conn, date(2026, 11, 3), "A.IS", date(2026, 11, 4), 100.0, date(2026, 11, 6), 104.0)
        p = S.performance(self.conn, lambda s: None)
        self.assertIsNone(p.bench_mean)
        self.assertIn("BIST 100 karşılaştırması yok", S.performance_text(p))


class CardRecordTest(Book):
    def test_ai_card_writes_its_reason(self):
        from core.screen import ai

        c = ai.Candidate("THYAO.IS", 250.0, 31.2, 14.0, 0.05, -0.4, 0.7)
        with mock.patch.object(ai, "candidates", return_value=[c]):
            ai.run(date(2026, 11, 4), {}, object(), validated=False, book=self.dir / "signals.db")
        row = self.conn.execute("SELECT reason, risk_tl, valid_until FROM signals").fetchone()
        self.assertIn("dip dönüşü", row["reason"])
        self.assertIn("RSI 31,2", row["reason"])
        self.assertIn("ML %70", row["reason"])
        self.assertGreater(row["risk_tl"], 0)
        self.assertEqual(row["valid_until"], "2026-11-04")
