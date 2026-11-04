"""
Fundamentals inbox (v0.99.50, K-70 madde 6): the user drops a CSV (downloaded from KAP by hand) into
data/inbox/temel/; the bot imports it with the existing checked import, moves it to islendi/ or
reddedildi/ and says what happened. No network, nothing is overwritten.
"""

import os
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path

from core.fundamentals import inbox as I
from core.fundamentals import store

HEADER = "symbol,period_end,published_at,item,value,unit,consolidated,inflation_adjusted,source\n"
GOOD = "THYAO,2026-06-30,2026-08-10T18:45:00+03:00,revenue,1000,TL,1,1,KAP elle\n"


class InboxTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.inbox = self.root / "inbox"
        self.inbox.mkdir()
        self.store = self.root / "fundamentals.csv"
        self.now = datetime(2026, 11, 4, 12, 0)

    def drop(self, name, text, age=120):
        p = self.inbox / name
        p.write_text(text, encoding="utf-8")
        old = time.time() - age
        os.utime(p, (old, old))
        return p

    def process(self):
        return I.process(self.inbox, self.store, self.now)

    def test_a_good_file_is_imported_and_moved(self):
        self.drop("thyao.csv", HEADER + GOOD)
        (result,) = self.process()
        self.assertEqual((result.added, result.rejected), (1, []))
        self.assertEqual(result.moved_to.parent.name, "islendi")
        self.assertFalse((self.inbox / "thyao.csv").exists())
        self.assertEqual(len(store.load(self.store)), 1)
        self.assertIn("1 satır eklendi", I.message(result))

    def test_bad_rows_are_counted_and_a_bad_file_is_rejected(self):
        self.drop("karisik.csv", HEADER + GOOD + "THYAO,2026-06-30,,revenue,x,TL,1,1,KAP\n")
        (mixed,) = self.process()
        self.assertEqual(mixed.added, 1)
        self.assertEqual(len(mixed.rejected), 1)
        self.assertIn("1 satır reddedildi", I.message(mixed))
        self.drop("bozuk.csv", "a,b\n1,2\n")
        (bad,) = self.process()
        self.assertEqual(bad.added, 0)
        self.assertEqual(bad.moved_to.parent.name, "reddedildi")
        self.assertTrue(bad.moved_to.with_suffix(".hata.txt").exists())

    def test_a_file_still_being_copied_waits(self):
        self.drop("yeni.csv", HEADER + GOOD, age=5)
        self.assertEqual(self.process(), [])
        self.assertTrue((self.inbox / "yeni.csv").exists())

    def test_the_same_name_twice_is_not_overwritten(self):
        self.drop("a.csv", HEADER + GOOD)
        first = self.process()[0].moved_to
        self.drop("a.csv", HEADER + GOOD)
        second = self.process()[0]
        self.assertNotEqual(first, second.moved_to)
        self.assertTrue(first.exists() and second.moved_to.exists())
        self.assertEqual(second.added, 0)  # already in the store: not added twice

    def test_empty_or_missing_inbox(self):
        self.assertEqual(I.process(self.root / "yok", self.store, self.now), [])


class JobTest(unittest.TestCase):
    def test_job_reports_each_file(self):
        import asyncio
        from types import SimpleNamespace
        from unittest import mock

        from bot import scheduler

        sent = []

        async def send_message(chat_id, text):
            sent.append(text)

        result = I.Result("a.csv", 2, [], Path("islendi/a.csv"))
        context = SimpleNamespace(bot=SimpleNamespace(send_message=send_message), job=SimpleNamespace(chat_id=7))
        with mock.patch.object(I, "process", return_value=[result]):
            asyncio.run(scheduler.fundamentals_inbox_job(context))
        self.assertEqual(len(sent), 1)
        self.assertIn("a.csv", sent[0])
        from telegram.ext import ApplicationBuilder

        app = ApplicationBuilder().token("123:abc").build()
        self.assertTrue(scheduler.schedule_fundamentals_inbox(app, 7))
        self.assertEqual(len(app.job_queue.get_jobs_by_name(scheduler.INBOX_JOB)), 1)
