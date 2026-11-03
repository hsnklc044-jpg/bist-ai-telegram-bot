"""
Independent second price source (v0.99.42, K-70 madde 3): a source from the primary is refused, an
unapproved network source never runs, fallback only between independent sources, none is
"ölçülemiyor", and a planted difference in a downloaded file is found.
"""

import asyncio
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

from core.market import second_source as S


class Fake:
    def __init__(self, name, origin, network=False, approved=None, terms=None, data=None, fail=False):
        self.info = S.SourceInfo(name, origin, network, approved, terms)
        self.data, self.fail, self.asked = data or {}, fail, 0

    async def closes(self, codes, start, end):
        self.asked += 1
        if self.fail:
            raise OSError("down")
        return self.data


def run(sources):
    return asyncio.run(S.verify(sources, ["AAA"], date(2026, 10, 1), date(2026, 10, 31)))


SERIES = {"AAA": pd.Series([10.0], index=pd.to_datetime(["2026-10-01"]))}


class RulesTest(unittest.TestCase):
    def test_the_primary_is_never_a_second_source(self):
        yahoo = Fake("yahoo-yedek", "Yahoo", data=SERIES)
        status, name, _ = run([yahoo])
        self.assertEqual((status, name), (S.Status.UNMEASURABLE, "bağımsız ikinci kaynak yok"))
        self.assertEqual(yahoo.asked, 0)  # not even asked

    def test_unapproved_network_source_never_runs(self):
        web = Fake("site", "site", network=True, data=SERIES)
        self.assertEqual(run([web])[0], S.Status.UNMEASURABLE)
        self.assertEqual(web.asked, 0)
        approved = Fake("site", "site", network=True, approved=date(2026, 11, 4), terms="DATA_SOURCES#site",
                        data=SERIES)
        self.assertEqual(run([approved])[:2], (S.Status.OK, "site"))

    def test_fallback_only_to_the_next_independent_source(self):
        down = Fake("a", "kurum-a", fail=True)
        yahoo = Fake("y", "yahoo", data=SERIES)
        good = Fake("b", "kurum-b", data=SERIES)
        status, name, got = run([down, yahoo, good])
        self.assertEqual((status, name), (S.Status.OK, "b"))
        self.assertEqual(yahoo.asked, 0)


class FileTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def test_comma_and_semicolon_files(self):
        a = self.dir / "a.csv"
        a.write_text("date,code,close\n2026-10-01,AAA.IS,10.5\n", encoding="utf-8")
        b = self.dir / "b.csv"
        b.write_text("Date;Code;Close\n01.10.2026;aaa;1.010,50\n", encoding="utf-8")
        self.assertEqual(S.read_price_file(a).iloc[0].tolist(), [pd.Timestamp("2026-10-01"), "AAA", 10.5])
        self.assertEqual(S.read_price_file(b).iloc[0].tolist(), [pd.Timestamp("2026-10-01"), "AAA", 1010.5])

    def test_bad_files_are_refused(self):
        p = self.dir / "c.csv"
        p.write_text("date,code\n2026-10-01,AAA\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "eksik sütun: close"):
            S.read_price_file(p)
        p.write_text("date,code,close\n2026-10-01,AAA,0\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "okunamadı"):
            S.read_price_file(p)

    def test_planted_difference_is_found(self):
        days = pd.bdate_range("2026-09-01", periods=30)
        close = pd.Series(100 * np.cumprod(1 + np.random.default_rng(0).normal(0, 0.01, 30)), index=days)
        ours = pd.DataFrame({"open": close, "high": close, "low": close, "close": close, "volume": 1.0})
        theirs = close.copy()
        theirs.iloc[15:] *= 1.05  # a 5% jump on one day only in their data: one return differs
        rows = [f"{d:%Y-%m-%d},AAA,{v:.4f}" for d, v in theirs.items()]
        rows += [f"{d:%Y-%m-%d},BBB,{v:.4f}" for d, v in close.items()]
        path = self.dir / "f.csv"
        path.write_text("date,code,close\n" + "\n".join(rows) + "\n", encoding="utf-8")
        with mock.patch("core.market.corrections.load_corporate_actions", return_value=[]):
            status, name, results, summary = S.check([S.FileSource(path, "aracı kurum")], ["AAA", "BBB"],
                                                     days[0].date(), days[-1].date(), bars=lambda s: ours)
        self.assertEqual(status, S.Status.OK)
        self.assertEqual(summary["checked"], 2)
        self.assertEqual(summary["differing"], ["AAA"])
        self.assertEqual(summary["source"], "dosya:f.csv")
        out = self.dir / "summary.json"
        S.save_summary(summary, out)
        self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["differing"], ["AAA"])


class SloTest(unittest.TestCase):
    def test_the_newer_summary_is_used_and_names_its_source(self):
        from datetime import datetime

        from core.reports import slo

        remote = {"disabled": True, "reason": "İş Yatırım kapalı"}
        local = {"date": "2026-11-04", "checked": 100, "differing": [], "source": "dosya:x.csv"}
        picked = slo.pick_accuracy(local, remote)
        result = slo.accuracy(datetime(2026, 11, 4, 20, 0), picked)
        self.assertEqual(result.state, slo.OK)
        self.assertIn("dosya:x.csv", result.text)
        self.assertIs(slo.pick_accuracy(None, remote), remote)  # no file: still "ölçülemiyor"
        older = {"date": "2026-10-01", "checked": 5, "differing": []}
        newer = {"date": "2026-10-20", "checked": 9, "differing": []}
        self.assertIs(slo.pick_accuracy(older, newer), newer)


class CommandTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        days = pd.bdate_range("2026-09-01", periods=10)
        self.ours = pd.DataFrame({"close": np.linspace(100, 110, 10)}, index=days)
        self.file = self.dir / "p.csv"
        self.file.write_text("date,code,close\n" + "\n".join(
            f"{d:%Y-%m-%d},AAA,{v:.4f}" for d, v in self.ours["close"].items()) + "\n", encoding="utf-8")

    def run_main(self, origin, bars=None):
        out = self.dir / "summary.json"
        with mock.patch.object(S, "SUMMARY_FILE", out), \
                mock.patch("core.market.corrections.load_corporate_actions", return_value=[]), \
                mock.patch("core.reports.daily.raw_bars", bars or (lambda s: self.ours)), \
                mock.patch("builtins.print"):
            code = S.main(["--dosya", str(self.file), "--kaynak", origin])
        return code, out

    def test_command_writes_the_summary(self):
        code, out = self.run_main("aracı kurum")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["checked"], 1)

    def test_a_yahoo_file_is_refused(self):
        code, out = self.run_main("yahoo")
        self.assertEqual(code, 1)
        self.assertFalse(out.exists())

    def test_one_broken_stock_does_not_stop_the_check(self):
        def broken(symbol):
            raise RuntimeError("db")

        code, out = self.run_main("aracı kurum", bars=broken)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["unchecked"], ["AAA"])
