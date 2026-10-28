"""
İleri hedef 1 (K-53): the elimination filter measured on forward data. Every session the stocks
the default /tara elimination removes ("elenen") and keeps ("kalan") are recorded with their own
source; /performans shows each group's later excess return over XU100 and their difference. The
exploration found the eliminated group −3,07% behind over 20 sessions; only forward data can
say whether that repeats.
"""

import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

from core.market.universe import BENCHMARK
from core.reports import forward
from core.signals_log import log_signal
from tests.helpers import make_ohlcv


def result(day, kept, eliminated):
    return SimpleNamespace(day=day, matches=[SimpleNamespace(symbol=s) for s in kept],
                           eliminated=[(s, why) for s, why in eliminated])


class RecordTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.log = Path(tmp.name) / "signal_log.csv"

    def rows(self):
        with open(self.log, encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh))

    def test_groups_are_recorded_once_per_day(self):
        r = result(date(2026, 10, 30), ["AAA.IS", "BBB.IS"], [("CCC.IS", "likidite 4 mn TL")])
        self.assertEqual(forward.log_elimination_groups(r, self.log), 3)
        self.assertEqual(forward.log_elimination_groups(r, self.log), 0)
        rows = self.rows()
        self.assertEqual({(x["symbol"], x["view"]) for x in rows},
                         {("AAA.IS", "kalan"), ("BBB.IS", "kalan"), ("CCC.IS", "elenen")})
        self.assertTrue(all(x["source"] == forward.ELIMINATION for x in rows))
        self.assertEqual([x["details"] for x in rows if x["view"] == "elenen"], ["likidite 4 mn TL"])

    def test_nothing_without_a_day(self):
        self.assertEqual(forward.log_elimination_groups(result(None, ["AAA.IS"], []), self.log), 0)


class ReportTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.log, self.equity = root / "signal_log.csv", root / "equity_log.csv"
        self.frames = {BENCHMARK: make_ohlcv(rows=300, seed=99)}
        for i in range(8):
            self.frames[f"S{i}.IS"] = make_ohlcv(rows=300, seed=10 + i)
        self.bars = lambda s: self.frames.get(s, pd.DataFrame())

    def test_section_with_too_few_records(self):
        text = forward.forward_report(self.log, self.equity, bars=self.bars)
        self.assertIn("🧹 Eleme filtresi (canlı)", text)
        self.assertIn("veri birikiyor", text)
        self.assertIn("−%3,07", text)  # the exploration reference is named

    def test_groups_and_difference_by_hand(self):
        index = self.frames["S0.IS"].index
        days = [index[i] for i in range(150, 250, 2)]
        for d in days:
            for s in ("S0.IS", "S1.IS", "S2.IS", "S3.IS"):
                log_signal(forward.ELIMINATION, s, 0, "kalan", d.date(), path=self.log)
            for s in ("S4.IS", "S5.IS"):
                log_signal(forward.ELIMINATION, s, 0, "elenen", d.date(), path=self.log)
        scored = forward.score_log(self.log, bars=self.bars)
        part = scored[(scored["source"] == forward.ELIMINATION) & (scored["horizon"] == 5)]
        kept = part[part["view"] == "kalan"].groupby("day")["excess"].mean()
        gone = part[part["view"] == "elenen"].groupby("day")["excess"].mean()
        expected = float((gone - kept).dropna().mean())

        lines = forward.elimination_lines(scored[scored["source"] == forward.ELIMINATION])
        five = next(line for line in lines if line.strip().startswith("5 seans"))
        self.assertIn("elenen", five)
        self.assertIn("kalan", five)
        self.assertIn(f"fark {forward.pct(expected)}", five)
        self.assertTrue(np.isfinite(expected))

        text = forward.forward_report(self.log, self.equity, bars=self.bars)
        self.assertNotIn("/top, /analyze ve /watchscan kayıtları", text)  # not counted as "asked"


class DailyTest(unittest.TestCase):
    def test_wired_into_the_evening_records(self):
        from unittest import mock

        from core.reports import daily

        with mock.patch("core.reports.forward.log_daily_scores", return_value=0), \
                mock.patch.object(daily, "_elimination_result", return_value=result(date(2026, 10, 30), ["A.IS"], [])), \
                mock.patch("core.reports.forward.log_elimination_groups", return_value=1) as logged:
            self.assertEqual(daily._record_scores(), "")
        logged.assert_called_once()

    def test_a_failure_is_a_warning_not_a_stop(self):
        from unittest import mock

        from core.reports import daily

        with mock.patch("core.reports.forward.log_daily_scores", return_value=0), \
                mock.patch.object(daily, "_elimination_result", side_effect=ValueError("bozuk")):
            warning = daily._record_scores()
        self.assertIn("Eleme ölçümü", warning)


if __name__ == "__main__":
    unittest.main()
