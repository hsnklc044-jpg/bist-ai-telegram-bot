"""
Red-team findings on the wave 1 package (v0.99.152): morning message length, data-quality false alarms,
the decision journal check in CI, filter results with a missing close, NaN in the morning table.
Synthetic data only; nothing touches the network or data/.
"""

import asyncio
import csv
import html
import math
import subprocess
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np
import pandas as pd

from core.market import quality, trust
from core.market.calendar import ISTANBUL
from core.market.corrections import CorporateAction
from core.reports import health
from core.research import karar_defteri as kd
from core.screen import command, subscriptions
from core.screen import filtre_kayitlari as fk
from core.screen import morning_table as mt

LIMIT = 4096
NOW = datetime(2026, 11, 19, 20, 0, tzinfo=ISTANBUL)
DAY = date(2026, 10, 28)


def noted(text):
    return trust.with_note(text, trust.Trust(3, "Yahoo"))


class MorningLengthTest(unittest.TestCase):
    """Finding 1: every morning message stays inside Telegram's 4096 characters."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        d = Path(tmp.name)
        self.paths = dict(path=d / "subs.csv", saved_path=d / "screens.csv")
        self.records = d / "filtre_kayitlari.csv"
        self.names = [f"tarama_uzun_ad_{i}" for i in range(8)]
        for name in self.names:
            command.save_text([name, "rsi<101", "ele=hayir"], path=self.paths["saved_path"], now=NOW)
        with open(self.paths["path"], "w", encoding="utf-8", newline="") as fh:
            out = csv.writer(fh, lineterminator="\n")
            out.writerow(subscriptions.COLUMNS)
            for name in self.names:  # 8 subscriptions (more than the command allows: the file decides)
                out.writerow([NOW.isoformat(), 7, name, subscriptions.SUBSCRIBE])
        idx = pd.bdate_range("2026-09-01", periods=5)
        self.frames = {f"HISSE{i:03d}.IS": pd.DataFrame({"close": np.full(5, 10.0 + i)}, index=idx)
                       for i in range(300)}

    def morning(self, live=None):
        def run(_query, frames, _bench, _found):
            return SimpleNamespace(matches=[SimpleNamespace(symbol=s, values={"gg_20": float(i)})
                                            for i, s in enumerate(frames)])

        with mock.patch("core.signals.store.locked", return_value=False), \
                mock.patch("core.market.calendar.is_session_day", return_value=True), \
                mock.patch("core.screen.engine.run", side_effect=run), \
                mock.patch.object(mt, "nearest_levels", return_value=(-12.345, 123.456, 12.5)):
            return subscriptions.morning(DAY, live=live or (lambda _s: (self.frames, None)), suspects=set(),
                                         universe_of=lambda *_: list(self.frames), usd=pd.Series(dtype=float),
                                         record_path=self.records, **self.paths)

    def test_many_rows_and_eight_screens_split_into_messages_under_the_limit(self):
        messages = self.morning()
        self.assertGreater(len(messages), 1)
        shown = []
        for i, text in enumerate(messages):
            sent = noted(text) if i == 0 else text  # the bot adds the data line to the first one
            self.assertLessEqual(len(sent), LIMIT, f"message {i + 1}")
            self.assertEqual(text.split("\n")[0], mt.WARNING)
            self.assertEqual(text.count("<pre>"), text.count("</pre>"))
            for block in text.split("<pre>")[1:]:
                body = block.split("</pre>")[0]
                self.assertNotIn("<", body)
                lines = [x for x in html.unescape(body).split("\n")[1:] if x.strip()]
                shown += [x.split()[0] for x in lines]
        self.assertEqual(sorted(shown), sorted(s.removesuffix(".IS") for s in self.frames))  # no row lost
        self.assertTrue(messages[-1].rstrip().endswith(command.DISCLAIMER))

    def test_long_failure_texts_are_cut(self):
        calls = {"n": 0}

        def live(_symbols):
            calls["n"] += 1
            if calls["n"] <= 3:
                raise ValueError("<x>" * 3000)
            return self.frames, None

        messages = self.morning(live=live)
        for i, text in enumerate(messages):
            self.assertLessEqual(len(noted(text) if i == 0 else text), LIMIT)
        failures = [line for m in messages for line in m.split("\n") if "hazırlanamadı" in line]
        self.assertEqual(len(failures), 3)
        for line in failures:
            self.assertLessEqual(len(html.unescape(line)), 300)

    def test_pack_never_exceeds_the_budget(self):
        rows = [mt.Row(f"COK_UZUN_SEMBOL_{i:04d}.IS", self.names, float(i), -1.0, 2.0, 3.0) for i in range(500)]
        code_of = mt.codes(self.names)
        parts = mt.table_parts(rows, code_of, 1000)
        self.assertTrue(all(len(p) <= 1000 for p in parts))
        self.assertEqual(sum(p.count("\n") for p in parts), 500)  # a header line in each part, then the rows
        packed = mt.pack([mt.WARNING, "baş"], parts + ["x" * 50] * 100, "devam", LIMIT)
        self.assertTrue(all(len(m) <= LIMIT for m in packed))
        self.assertTrue(all(m.startswith(mt.WARNING + "\n") for m in packed))

    def test_one_failing_send_does_not_lose_the_others(self):
        from bot import scheduler

        got = []

        async def send_message(chat_id, text, **kw):
            if text == "iki":
                raise RuntimeError("telegram")
            got.append(text)

        context = SimpleNamespace(bot=SimpleNamespace(send_message=send_message), job=SimpleNamespace(chat_id=7))
        with mock.patch("core.screen.subscriptions.morning", return_value=["bir", "iki", "üç"]):
            asyncio.run(scheduler.morning_screens_job(context))
        self.assertEqual(got[:1] + got[-1:], ["bir", "üç"])


def series_frame(closes, days):
    c = pd.Series(closes, index=pd.DatetimeIndex([pd.Timestamp(d) for d in days]), dtype=float)
    return pd.DataFrame({"open": c, "high": c, "low": c, "close": c, "volume": 1000.0})


SYMBOLS = ["XU100.IS", *[f"S{i:02d}.IS" for i in range(20)]]


def universe(**changes):
    days = quality.recent_sessions(date(2026, 11, 19), 45)
    frames = {s: series_frame([100.0 + i * 0.1 for i in range(len(days))], days) for s in SYMBOLS}
    for symbol, change in changes.items():
        frames[symbol] = change(frames[symbol].copy(), days)
    return frames, days


def check(frames, actions=()):
    return health.data_quality_check(NOW, symbols=list(frames), read=lambda s, start=None: frames[s],
                                     exceptions=[], actions=list(actions))


def step(factor, back):
    def change(df, days):
        df.loc[df.index >= pd.Timestamp(days[-back]), ["open", "high", "low", "close"]] *= factor
        return df
    return change


def stale(back):
    return lambda df, days: df[df.index < pd.Timestamp(days[-back])]


class DataQualityFalseAlarmTest(unittest.TestCase):
    """Finding 2."""

    def test_moves_between_10_5_and_20_percent_are_an_info_count(self):
        frames, _ = universe(**{"S03.IS": step(1.15, 4)})
        got = check(frames)
        self.assertEqual(got.state, health.INFO, got.text)
        self.assertIn("1", got.text)
        self.assertNotIn("S03 ", got.text)  # a count, not a list

    def test_move_beyond_20_percent_is_a_possible_unadjusted_jump(self):
        frames, _ = universe(**{"S03.IS": step(0.5, 4)})
        got = check(frames)
        self.assertEqual(got.state, health.WARN)
        self.assertIn("olası düzeltilmemiş sıçrama", got.text)
        self.assertIn("S03", got.text)

    def test_a_known_corporate_action_day_is_not_flagged(self):
        frames, days = universe(**{"S03.IS": step(0.5, 4)})
        known = CorporateAction("S03.IS", days[-4], 2.0, "test")
        self.assertNotEqual(check(frames, [known]).state, health.WARN)

    def test_one_halted_stock_is_one_info_line(self):
        frames, _ = universe(**{"S05.IS": stale(25)})
        got = check(frames)
        self.assertEqual(got.state, health.INFO, got.text)
        self.assertIn("S05", got.text)
        self.assertNotIn("\n", got.text)

    def test_stale_index_or_many_stale_stocks_warn(self):
        frames, _ = universe(**{"XU100.IS": stale(3)})
        self.assertEqual(check(frames).state, health.WARN)
        frames, _ = universe(**{s: stale(3) for s in SYMBOLS[1:4]})  # 3 of 21 > 10%
        self.assertEqual(check(frames).state, health.WARN)

    def test_guidance_names_the_effect(self):
        from bot import scheduler

        effect, _todo = scheduler.GUIDANCE["Veri kalitesi"]
        self.assertIn("otomatik", effect)
        self.assertIn("Veri kalitesi", scheduler.SEVERITY)


class JournalInCiTest(unittest.TestCase):
    """Finding 3: the committed journal rows are checked against the bot branch (or the previous commit)."""

    def test_project_journal_old_rows_unchanged_since_base(self):
        ref = kd.base_ref()
        if ref is None:
            self.skipTest("git ya da karşılaştırılacak commit yok")
        self.assertEqual(kd.verify(kd.JOURNAL, ref=ref), [])

    def test_missing_git_or_ref_is_unverified_not_clean(self):
        got = kd.verify(kd.JOURNAL, ref="yok-boyle-bir-ref-123")
        self.assertEqual(len(got), 1)
        self.assertTrue(got[0].startswith(kd.UNVERIFIED))
        with mock.patch("subprocess.run", side_effect=OSError("git yok")):
            got = kd.verify(kd.JOURNAL)
            self.assertTrue(got and got[0].startswith(kd.UNVERIFIED))
            self.assertIsNone(kd.base_ref())

    def test_an_edited_committed_row_is_caught(self):
        try:
            subprocess.run(["git", "--version"], capture_output=True, check=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            self.skipTest("git yok")
        if kd.committed_text(ref="HEAD") is None:
            self.skipTest("HEAD'de defter yok")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "KARAR_DEFTERI.csv"
            rows = kd.read(kd.JOURNAL)
            kd._write_rows([dict(rows[0], ozet="değişti"), *rows[1:]], path)
            with mock.patch.object(kd, "committed_text", return_value=kd.JOURNAL.read_text(encoding="utf-8")):
                self.assertTrue(kd.verify(path, ref="HEAD"))


class FilterResultRetryTest(unittest.TestCase):
    """Finding 4: no close on the 20th session -> retry; after 10 more sessions a final 'veri yok' row."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        d = Path(tmp.name)
        self.records, self.results = d / "filtre_kayitlari.csv", d / "filtre_sonuclari.csv"
        self.days = pd.bdate_range("2026-09-01", periods=50)
        self.prices = {"XU100.IS": pd.DataFrame({"close": np.linspace(100, 110, 50)}, index=self.days),
                       "LATE.IS": pd.DataFrame({"close": np.linspace(10, 12, 10)}, index=self.days[:10])}
        fk.append_records([fk.Record("LATE", ["x"], self.days[2].date(), 10.1)], self.days[3].date(), self.records)

    def fill(self, i):
        return fk.fill_results(self.days[i].date(), records=self.records, results=self.results,
                               read=lambda s: self.prices[s], usd=pd.Series(dtype=float), cpi=pd.DataFrame())

    def rows(self):
        return list(csv.DictReader(self.results.read_text(encoding="utf-8").splitlines()))

    def test_retries_then_catches_up(self):
        self.assertEqual(self.fill(25), [])  # 20th session = days[22], no close yet
        self.assertFalse(self.results.exists())
        self.prices["LATE.IS"] = pd.DataFrame({"close": np.linspace(10, 12, 50)}, index=self.days)  # store caught up
        self.assertEqual(len(self.fill(26)), 1)
        row = self.rows()[0]
        self.assertNotEqual(row["nominal_yuzde"], "")
        self.assertEqual(row["not"], "")

    def test_final_veri_yok_after_ten_more_sessions(self):
        self.assertEqual(self.fill(31), [])  # 9 sessions after the 20th
        self.assertEqual(len(self.fill(32)), 1)  # 10 sessions after
        row = self.rows()[0]
        self.assertEqual((row["nominal_yuzde"], row["not"]), ("", "veri yok"))
        self.assertEqual(self.fill(40), [])  # final: never written again

    def test_new_record_files_have_no_empty_result_columns(self):
        header = self.records.read_text(encoding="utf-8").splitlines()[0].split(",")
        self.assertFalse([c for c in header if c.startswith("sonuc_")])

    def test_old_record_file_still_read_and_appended(self):
        old = self.records.with_name("eski.csv")
        old.write_text("kayit_tarihi,hisse,filtreler,referans_tarihi,referans_kapanis,sonuc_nominal,"
                       "sonuc_xu100_goreli,sonuc_usd,sonuc_reel\n2026-09-04,LATE,x,2026-09-03,10.1,,,,\n",
                       encoding="utf-8")
        fk.append_records([fk.Record("LATE", ["y"], self.days[4].date(), 10.2)], self.days[5].date(), old)
        rows = list(csv.DictReader(old.read_text(encoding="utf-8").splitlines()))
        self.assertEqual([r["hisse"] for r in rows], ["LATE", "LATE"])
        self.assertEqual(rows[1]["referans_kapanis"], "10.2")
        self.assertEqual(rows[1]["sonuc_reel"], "")


class NanDisplayTest(unittest.TestCase):
    """Finding 5."""

    def test_pct_nan_is_a_dash(self):
        self.assertEqual(mt._pct(float("nan")), "—")
        self.assertEqual(mt._pct(np.float64("nan")), "—")
        self.assertEqual(mt.atr_label(np.float64("nan")), "—")

    def test_nearest_levels_ignore_nan(self):
        from core.analytics.levels import Level

        def lv(price, kind, atr, pct):
            return Level(price, kind, "küme", 50, 2, None, 0, atr, pct)

        found = [lv(float("nan"), "destek", float("nan"), float("nan")), lv(9.0, "destek", -1.5, -10.0),
                 lv(float("nan"), "direnç", -0.1, 0.1), lv(11.0, "direnç", float("nan"), float("nan"))]
        df = pd.DataFrame({"close": [10.0]})
        for order in (found, found[::-1]):
            with mock.patch("core.analytics.levels.levels", return_value=order):
                sup, res, dist = mt.nearest_levels(df)
            self.assertEqual(sup, -10.0)
            self.assertTrue(res is None or math.isnan(res))
            self.assertEqual(dist, 1.5)
        row = mt.Row("AAA.IS", ["x"], 1.0, -10.0, float("nan"), float("nan"))
        table = mt.table([row], {"x": "X"})
        self.assertIn("-10,0/—", table)
        self.assertNotIn("nan", table.lower())


if __name__ == "__main__":
    unittest.main()
