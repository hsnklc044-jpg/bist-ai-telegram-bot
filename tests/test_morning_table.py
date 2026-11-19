"""
Owner's instruction #15: one morning table (one row per stock), duplicate screens only as codes,
the untested-filter warning first, an append-only filter record and its 20-session results file
filled by the weekday evening job. Synthetic data only; nothing touches the network or data/.
"""

import asyncio
import csv
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np
import pandas as pd

from core.market import trust
from core.market.calendar import ISTANBUL
from core.screen import command, subscriptions
from core.screen import filtre_kayitlari as fk
from core.screen import morning_table as mt
from tests.test_screen import market

NOW = datetime(2026, 10, 28, 20, 0, tzinfo=ISTANBUL)
DAY = date(2026, 10, 28)
WARNING = "Bu filtreler henüz test edilmedi (testler 18.12 sonrası). Filtre sonucudur, karar dayanağı değildir."


def series(values, start="2025-01-01"):
    return pd.Series(values, index=pd.bdate_range(start, periods=len(values)), dtype=float)


class PureTest(unittest.TestCase):
    def test_warning_text_is_exact(self):
        self.assertEqual(mt.WARNING, WARNING)

    def test_noise_label_below_one_atr(self):
        self.assertEqual(mt.atr_label(0.4), "gürültü içinde")
        self.assertEqual(mt.atr_label(-0.99), "gürültü içinde")
        self.assertEqual(mt.atr_label(1.0), "1,0")
        self.assertEqual(mt.atr_label(2.345), "2,3")
        self.assertEqual(mt.atr_label(None), "—")

    def test_usd_trend_arrows_and_missing(self):
        rate = series(np.full(260, 30.0))
        up = series(np.r_[np.full(240, 100.0), np.full(20, 150.0)])
        down = series(np.r_[np.full(240, 100.0), np.full(20, 60.0)])
        self.assertEqual(mt.usd_trend(up, rate), "↑")
        self.assertEqual(mt.usd_trend(down, rate), "↓")
        self.assertEqual(mt.usd_trend(up, pd.Series(dtype=float)), "—")  # no rates
        self.assertEqual(mt.usd_trend(up.iloc[-150:], rate), "—")  # fewer than 200 USD prices
        self.assertEqual(mt.usd_trend(up, rate.iloc[:-1]), "—")  # no rate on the last close day
        # USD price = close / USDTRY of the same day: a rising rate turns a flat TL price down
        flat = series(np.full(260, 100.0))
        rising = series(np.r_[np.full(240, 30.0), np.full(20, 40.0)])
        self.assertEqual(mt.usd_trend(flat, rising), "↓")

    def test_overlaps_reports_subsets_and_identical_screens(self):
        found = mt.overlaps({"bist100_aday": {"A", "B", "C"}, "bist30_aday": {"A"}, "kopya": {"A", "B", "C"},
                             "bist100_trend": {"B", "D"}, "bos": set()})
        self.assertIn(("bist30_aday", "bist100_aday", "alt küme"), found)
        self.assertIn(("kopya", "bist100_aday", "aynı"), found)  # identical: reported once
        self.assertNotIn(("bist100_aday", "kopya", "aynı"), found)
        self.assertFalse([f for f in found if "bist100_trend" in f[:2] and f[2] == "aynı"])
        self.assertFalse([f for f in found if f[0] == "bos"])  # an empty list is no evidence
        self.assertNotIn(("bist30_aday", "bist100_trend", "alt küme"), found)

    def test_codes_are_short_and_unique(self):
        codes = mt.codes(["bist100_aday", "bist30_aday", "bist100_trend", "bist100_geri_cekilme",
                          "bist100_kirilim", "baska", "baskb"])
        self.assertEqual(codes["bist100_aday"], "A100")
        self.assertEqual(codes["bist30_aday"], "A30")
        self.assertEqual(len(set(codes.values())), len(codes))
        self.assertTrue(all(len(c) <= 5 for c in codes.values()))

    def test_event_flag_hook_is_empty_for_now(self):
        self.assertEqual(mt.event_flag("GARAN.IS", DAY), "—")

    def test_verified_data_line_is_one_switch(self):
        self.assertEqual(trust.note_line(), "Veri: doğrulanmamış kaynak")
        text = trust.with_note("başlık\ngövde", trust.Trust(3, "Yahoo"))
        self.assertEqual(text.split("\n")[1], "Veri: doğrulanmamış kaynak")
        with mock.patch.object(trust, "VERIFIED_ON", date(2026, 12, 20)):
            self.assertEqual(trust.note_line(), "Veri: doğrulandı (20.12.2026)")
            text = trust.with_note("başlık\ngövde", trust.Trust(3, "Yahoo"))
            self.assertEqual(text.split("\n")[1], "Veri: doğrulandı (20.12.2026)")


class MorningTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        d = Path(tmp.name)
        self.paths = dict(path=d / "subs.csv", saved_path=d / "screens.csv")
        self.records = d / "filtre_kayitlari.csv"
        self.frames, self.bench = market()
        command.save_text(["dusuk", "rsi<30", "ele=hayir"], path=self.paths["saved_path"], now=NOW)
        command.save_text(["dusuk2", "rsi<30", "ele=hayir"], path=self.paths["saved_path"], now=NOW)  # identical
        command.save_text(["genis", "rsi<101", "ele=hayir"], path=self.paths["saved_path"], now=NOW)
        for name in ("dusuk", "dusuk2", "genis"):
            subscriptions.subscribe_text([name], 7, now=NOW, **self.paths)

    def morning(self, day=DAY, **extra):
        kwargs = dict(live=lambda _s: (self.frames, self.bench), suspects=set(),
                      universe_of=lambda *_: list(self.frames), usd=pd.Series(dtype=float),
                      record_path=self.records, **self.paths)
        kwargs.update(extra)
        with mock.patch("core.signals.store.locked", return_value=False), \
                mock.patch("core.market.calendar.is_session_day", return_value=True):
            return subscriptions.morning(day, **kwargs)

    def test_one_message_one_row_per_stock_warning_first(self):
        messages = self.morning()
        self.assertEqual(len(messages), 1)
        text = messages[0]
        self.assertEqual(text.split("\n")[0], WARNING)
        table = text.split("<pre>")[1].split("</pre>")[0]
        rows = [line for line in table.split("\n")[1:] if line.strip()]
        names = [r.split()[0] for r in rows]
        self.assertEqual(len(names), len(set(names)))  # one row per stock
        self.assertEqual(len(names), 20)  # genis matches every stock
        s00 = next(r for r in rows if r.startswith("S00 "))
        self.assertEqual(len(s00.split()[1].split(",")), 3)  # codes of all three screens it passed
        for row in rows:
            self.assertTrue(row.rstrip().endswith("—"))  # no USD rate given -> "—"
        self.assertTrue(text.rstrip().endswith(command.DISCLAIMER))
        noted = trust.with_note(text, trust.Trust(3, "Yahoo"))
        self.assertEqual(noted.split("\n")[:2], [WARNING, trust.NOTE])
        for word in (" al ", " sat ", "fırsat", "güçlü"):
            self.assertNotIn(word, text.replace(command.DISCLAIMER, "").lower())

    def test_ranks_are_by_relative_strength(self):
        text = self.morning()[0]
        table = text.split("<pre>")[1].split("</pre>")[0]
        rows = [line.split() for line in table.split("\n")[1:] if line.strip()]
        ranks = [int(r[2]) for r in rows]
        self.assertEqual(sorted(ranks), list(range(1, 21)))

    def test_html_is_escaped(self):
        text = self.morning()[0]
        outside = text.replace("<pre>", "").replace("</pre>", "")
        self.assertNotIn("<", outside)  # rsi<30 is written as &lt;

    def test_record_is_append_only_and_once_per_day_per_stock(self):
        self.morning()
        first = self.records.read_text(encoding="utf-8")
        rows = list(csv.DictReader(first.splitlines()))
        self.assertEqual(len(rows), 20)
        self.assertEqual(list(rows[0]), list(fk.RECORD_COLUMNS))
        s00 = next(r for r in rows if r["hisse"] == "S00")
        self.assertEqual(s00["kayit_tarihi"], DAY.isoformat())
        self.assertEqual(s00["referans_tarihi"], self.frames["S00.IS"].index[-1].date().isoformat())
        self.assertAlmostEqual(float(s00["referans_kapanis"]), float(self.frames["S00.IS"]["close"].iloc[-1]), 4)
        self.assertEqual(sorted(s00["filtreler"].split(";")), ["dusuk", "dusuk2", "genis"])
        self.morning()  # the same day again: nothing new
        self.assertEqual(self.records.read_text(encoding="utf-8"), first)
        self.morning(day=date(2026, 10, 29))
        after = self.records.read_text(encoding="utf-8")
        self.assertTrue(after.startswith(first))
        self.assertEqual(len(list(csv.DictReader(after.splitlines()))), 40)

    def test_record_failure_does_not_stop_the_message(self):
        with mock.patch.object(fk, "append_records", side_effect=OSError("disk")):
            messages = self.morning()
        self.assertEqual(len(messages), 1)
        self.assertIn("<pre>", messages[0])

    def test_one_failing_screen_is_a_line_in_the_same_message(self):
        calls = {"n": 0}

        def live(symbols):
            calls["n"] += 1
            if calls["n"] == 1:
                raise ValueError("yok")
            return self.frames, self.bench

        messages = self.morning(live=live)
        self.assertEqual(len(messages), 1)
        self.assertIn("hazırlanamadı", messages[0])
        self.assertIn("<pre>", messages[0])

    def test_noise_label_in_the_table(self):
        from core.analytics.levels import Level

        def near(_found, _k):
            return {"destek": [Level(9.0, "destek", "küme", 50, 2, None, 0, -0.5, -2.0)],
                    "direnç": [Level(11.0, "direnç", "küme", 50, 2, None, 0, 3.0, 5.0)]}

        with mock.patch("core.analytics.levels.nearest", side_effect=near):
            text = self.morning()[0]
        self.assertIn("gürültü içinde", text)
        self.assertIn("-2,0/+5,0", text)


class ResultsTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        d = Path(tmp.name)
        self.records, self.results = d / "filtre_kayitlari.csv", d / "filtre_sonuclari.csv"
        days = pd.bdate_range("2026-09-01", periods=40)
        self.days = days
        self.prices = {
            "XU100.IS": pd.DataFrame({"close": np.linspace(100, 110, 40)}, index=days),
            "AAA.IS": pd.DataFrame({"close": np.linspace(10, 12, 40)}, index=days),
            "BBB.IS": pd.DataFrame({"close": np.linspace(10, 12, 5)}, index=days[:5]),  # stopped trading
        }
        self.ref = days[2].date()
        fk.append_records([fk.Record("AAA", ["x"], self.ref, 10.1), fk.Record("BBB", ["x"], self.ref, 10.1)],
                          days[3].date(), self.records)

    def read(self, symbol):
        if symbol == "BAD.IS":
            raise ValueError("bozuk")
        return self.prices[symbol]

    def fill(self, today, **extra):
        kwargs = dict(records=self.records, results=self.results, read=self.read,
                      usd=pd.Series(30.0, index=self.days), cpi=pd.DataFrame())
        kwargs.update(extra)
        return fk.fill_results(today, **kwargs)

    def rows(self):
        return list(csv.DictReader(self.results.read_text(encoding="utf-8").splitlines()))

    def test_waits_until_20_sessions_have_passed(self):
        self.assertEqual(self.fill(self.days[21].date()), [])  # 19 sessions after the reference
        self.assertFalse(self.results.exists())

    def test_fills_four_returns_and_leaves_missing_data_empty(self):
        lines = self.fill(self.days[30].date())
        self.assertEqual(len(lines), 2)
        rows = {r["hisse"]: r for r in self.rows()}
        a = rows["AAA"]
        end = self.days[22]
        self.assertEqual(a["bitis_tarihi"], end.date().isoformat())
        close = float(self.prices["AAA.IS"]["close"].loc[end])
        nominal = close / 10.1 - 1
        self.assertAlmostEqual(float(a["nominal_yuzde"]), 100 * nominal, 3)
        bench = self.prices["XU100.IS"]["close"]
        xu = bench.loc[end] / bench.loc[pd.Timestamp(self.ref)] - 1
        self.assertAlmostEqual(float(a["xu100_goreli_yuzde"]), 100 * (nominal - xu), 3)
        self.assertAlmostEqual(float(a["usd_yuzde"]), 100 * nominal, 3)  # flat rate
        self.assertEqual(a["reel_yuzde"], "")  # no CPI: empty, never guessed
        b = rows["BBB"]
        self.assertEqual((b["nominal_yuzde"], b["xu100_goreli_yuzde"], b["usd_yuzde"]), ("", "", ""))

    def test_results_are_append_only_and_written_once(self):
        self.fill(self.days[30].date())
        first = self.results.read_text(encoding="utf-8")
        self.assertEqual(self.fill(self.days[31].date()), [])
        self.assertEqual(self.results.read_text(encoding="utf-8"), first)
        fk.append_records([fk.Record("AAA", ["y"], self.days[4].date(), 10.2)], self.days[5].date(), self.records)
        self.fill(self.days[35].date())
        after = self.results.read_text(encoding="utf-8")
        self.assertTrue(after.startswith(first))
        self.assertEqual(len(self.rows()), 3)

    def test_a_bad_record_is_skipped(self):
        fk.append_records([fk.Record("BAD", ["x"], self.ref, 10.0)], self.days[3].date(), self.records)
        with self.records.open("a", encoding="utf-8") as fh:
            fh.write("2026-09-04,CCC,x,tarih-degil,abc,,,,\n")
        lines = self.fill(self.days[30].date())
        self.assertEqual(sorted(r["hisse"] for r in self.rows()), ["AAA", "BBB"])
        self.assertEqual(len(lines), 2)

    def test_no_records_no_file(self):
        self.records.unlink()
        self.assertEqual(self.fill(self.days[30].date()), [])
        self.assertFalse(self.results.exists())


class EveningJobTest(unittest.TestCase):
    def run_job(self):
        from bot import scheduler

        sent = []

        async def send_message(chat_id, text, **_kw):
            sent.append(text)

        context = SimpleNamespace(bot=SimpleNamespace(send_message=send_message), job=SimpleNamespace(chat_id=7))
        asyncio.run(scheduler.prediction_ledger_job(context))
        return sent

    def test_evening_job_fills_filter_results_without_a_message(self):
        with mock.patch("core.research.tahmin_defteri.daily", return_value=[]), \
                mock.patch("core.screen.filtre_kayitlari.fill_results", return_value=["AAA 2026-10-01"]) as fill:
            sent = self.run_job()
        fill.assert_called_once()
        self.assertEqual(sent, [])

    def test_evening_job_survives_a_filter_results_failure(self):
        with mock.patch("core.research.tahmin_defteri.daily", return_value=["T1"]), \
                mock.patch("core.screen.filtre_kayitlari.fill_results", side_effect=RuntimeError("bozuk")):
            sent = self.run_job()
        self.assertEqual(len(sent), 1)  # the ledger message still goes out

    def test_morning_job_sends_html(self):
        from bot import scheduler

        got = []

        async def send_message(chat_id, text, **kw):
            got.append(kw)

        context = SimpleNamespace(bot=SimpleNamespace(send_message=send_message), job=SimpleNamespace(chat_id=7))
        with mock.patch("core.screen.subscriptions.morning", return_value=["<pre>x</pre>"]):
            asyncio.run(scheduler.morning_screens_job(context))
        self.assertEqual(got, [{"parse_mode": "HTML"}])


if __name__ == "__main__":
    unittest.main()
