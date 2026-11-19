"""K-112: the bot marks due ledger rows every weekday; results live in data/, the tracked ledger is never written."""

import asyncio
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pandas as pd
from telegram.ext import ApplicationBuilder

from bot import scheduler
from core.market.calendar import ISTANBUL
from core.reports import piyasa_notu
from core.research import tahmin_defteri as td


def _closes(*values, start="2026-11-20"):
    return pd.Series(values, index=pd.bdate_range(start, periods=len(values)), dtype=float)


class DailyMarkingTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.ledger = self.dir / "TAHMIN_DEFTERI.csv"
        shutil.copy(td.LEDGER, self.ledger)
        self.results = self.dir / "data" / "tahmin_sonuclari.csv"

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def run_daily(self, today, closes):
        return td.daily(today, ledger=self.ledger, results=self.results, closes_for=lambda s: closes)

    def test_due_row_marked_into_results_file_and_ledger_untouched(self):
        before = self.ledger.read_bytes()
        # ASELS row: trigger close > 350, target 360, deadline 2026-12-03
        lines = self.run_daily(date(2026, 12, 4), _closes(349, 352, 361, *[355] * 8))
        self.assertEqual(self.ledger.read_bytes(), before)
        self.assertTrue(self.results.exists())
        rows = {r["id"]: r for r in td.read_with_results(self.ledger, self.results)}
        self.assertEqual((rows["T-20261119-1"]["sonuc"], rows["T-20261119-1"]["sonuc_tarihi"]), ("tuttu", "2026-11-24"))
        self.assertEqual(len(lines), 1)
        self.assertIn("T-20261119-1", lines[0])
        self.assertIn("tuttu", lines[0])

    def test_nothing_due_means_no_message_and_no_file(self):
        self.assertEqual(self.run_daily(date(2026, 11, 25), _closes(361)), [])
        self.assertFalse(self.results.exists())

    def test_marked_once_only(self):
        series = _closes(349, 352, 361, *[355] * 8)
        self.assertEqual(len(self.run_daily(date(2026, 12, 4), series)), 1)
        self.assertEqual(self.run_daily(date(2026, 12, 5), series), [])

    def test_manual_rows_never_marked(self):
        self.run_daily(date(2027, 1, 30), _closes(*[100] * 60))
        rows = {r["id"]: r for r in td.read_with_results(self.ledger, self.results)}
        for rid in ("T-20261119-2", "T-20261119-3", "T-20261119-4", "T-20261119-6", "T-20261119-7"):
            self.assertEqual(rows[rid]["sonuc"], "", rid)

    def test_message_is_a_record_not_advice(self):
        lines = self.run_daily(date(2026, 12, 4), _closes(349, 352, 361, *[355] * 8))
        text = td.message(lines)
        self.assertIn("yatırım tavsiyesi değildir", text)
        self.assertEqual(len(text.splitlines()), 3)
        self.assertEqual(piyasa_notu.problems(text.replace("yatırım tavsiyesi değildir", "")), [])


class DefaultsAndBadRowsTest(unittest.TestCase):
    """Red-team finding: the bot calls daily(today) with no paths; that call must work."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.ledger = self.dir / "TAHMIN_DEFTERI.csv"
        shutil.copy(td.LEDGER, self.ledger)
        self.results = self.dir / "tahmin_sonuclari.csv"

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_daily_with_default_paths(self):
        with mock.patch.object(td, "LEDGER", self.ledger), mock.patch.object(td, "RESULTS", self.results):
            lines = td.daily(date(2026, 12, 4), closes_for=lambda s: _closes(349, 352, 361, *[355] * 8))
        self.assertEqual(len(lines), 1)
        self.assertTrue(self.results.exists())

    def test_missing_ledger_is_quiet(self):
        self.assertEqual(td.daily(date(2026, 12, 4), ledger=self.dir / "yok.csv", results=self.results), [])

    def test_bad_row_and_bad_symbol_do_not_stop_the_rest(self):
        rows = td.read(self.ledger)
        bad = dict(rows[0], id="T-BOZUK", hedef_seviye="abc")
        nodata = dict(rows[0], id="T-VERIYOK", sembol="YOK.IS")
        td.write([bad, nodata, *rows], self.ledger)

        def closes_for(symbol):
            if symbol == "YOK.IS":
                raise KeyError(symbol)
            return _closes(349, 352, 361, *[355] * 8)

        lines = td.daily(date(2026, 12, 4), ledger=self.ledger, results=self.results, closes_for=closes_for)
        self.assertEqual([x.split(" ")[0] for x in lines], ["T-20261119-1"])


class LedgerJobTest(unittest.TestCase):
    def test_weekday_evening_job_registered(self):
        app = ApplicationBuilder().token("123:ABC").build()
        self.assertTrue(scheduler.schedule_prediction_ledger(app, 42))
        jobs = app.job_queue.get_jobs_by_name(scheduler.LEDGER_JOB)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].chat_id, 42)
        self.assertEqual(scheduler.LEDGER_AT.tzinfo, ISTANBUL)
        self.assertGreater((scheduler.LEDGER_AT.hour, scheduler.LEDGER_AT.minute), (18, 30))

    def test_job_sends_only_when_something_was_marked(self):
        sent = []

        async def send(chat, text):
            sent.append((chat, text))

        ctx = SimpleNamespace(job=SimpleNamespace(chat_id=7), bot=SimpleNamespace(send_message=send))
        with mock.patch("core.research.tahmin_defteri.daily", return_value=[]):
            asyncio.run(scheduler.prediction_ledger_job(ctx))
        self.assertEqual(sent, [])
        with mock.patch("core.research.tahmin_defteri.daily", return_value=["T-1 (AAA): tuttu, 2026-12-01"]):
            asyncio.run(scheduler.prediction_ledger_job(ctx))
        self.assertEqual(len(sent), 1)
        self.assertIn("T-1", sent[0][1])


if __name__ == "__main__":
    unittest.main()
