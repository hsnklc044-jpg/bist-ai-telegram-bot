import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import pandas as pd

from core.market.universe import BENCHMARK
from core.reports import forward
from core.signals_log import log_signal
from tests.helpers import make_ohlcv


def _bars(frames: dict[str, pd.DataFrame]):
    return lambda symbol: frames.get(symbol, pd.DataFrame())


def _flat(values_open, values_close, start="2026-10-01"):
    index = pd.bdate_range(start, periods=len(values_close))
    return pd.DataFrame(
        {"open": values_open, "high": values_close, "low": values_close, "close": values_close,
         "volume": 1_000_000.0},
        index=index,
        dtype=float,
    )


class ForwardExcessTest(unittest.TestCase):
    def test_enters_next_open_and_subtracts_market(self):
        stock = _flat([10, 11, 12, 13], [10, 12, 13, 14])
        bench = _flat([100, 100, 100, 100], [100, 100, 105, 110])
        day = stock.index[0].date()

        # buy at open of day 2 (11), sell at close of day 3 (13): +18.18%; XU100 100 -> 105: +5%
        excess = forward.forward_excess(stock, bench, day, horizon=2)
        self.assertAlmostEqual(excess, 13 / 11 - 1 - 0.05)

    def test_none_until_the_horizon_has_passed(self):
        stock = _flat([10, 11], [10, 12])
        self.assertIsNone(forward.forward_excess(stock, stock, stock.index[0].date(), horizon=5))


class SummaryTest(unittest.TestCase):
    def test_interval_is_over_days_not_records(self):
        rows = pd.DataFrame(
            {"view": "Pozitif", "day": [1, 1, 1, 2, 2, 2], "excess": [0.1, 0.1, 0.1, -0.1, -0.1, -0.1]}
        )
        stats = forward.summarize(rows)

        self.assertEqual((stats.records, stats.days), (6, 2))
        self.assertAlmostEqual(stats.mean, 0.0)
        self.assertLess(stats.low, -0.1)  # two independent days, not six
        self.assertFalse(stats.mature)
        self.assertIn("henüz karar yok (2/20 gün)", forward._verdict(stats))

    def test_verdicts_when_mature(self):
        up = forward.ViewStats("Pozitif", 400, 20, 0.02, 0.01, 0.03, 0.6)
        flat = forward.ViewStats("Nötr", 400, 20, 0.0, -0.01, 0.01, 0.5)
        self.assertIn("geçiyor", forward._verdict(up))
        self.assertIn("anlamlı değil", forward._verdict(flat))


class RecordingAndReportTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.log = self.root / "signal_log.csv"
        self.equity = self.root / "equity_log.csv"
        self.frames = {
            BENCHMARK: make_ohlcv(rows=300, seed=99),
            "AAA.IS": make_ohlcv(rows=300, seed=1),
            "BBB.IS": make_ohlcv(rows=300, seed=2),
            "NEW.IS": make_ohlcv(rows=20, seed=3),  # too short to score
        }
        self.bars = _bars(self.frames)

    def _rows(self):
        with open(self.log, encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh))

    def test_daily_scores_recorded_once_per_day(self):
        universe = ["AAA.IS", "BBB.IS", "NEW.IS", "GONE.IS"]

        first = forward.log_daily_scores(universe, self.log, bars=self.bars)
        again = forward.log_daily_scores(universe, self.log, bars=self.bars)

        self.assertEqual((first, again), (2, 0))
        rows = self._rows()
        self.assertEqual({r["symbol"] for r in rows}, {"AAA.IS", "BBB.IS"})
        self.assertTrue(all(r["source"] == "daily" for r in rows))
        self.assertEqual(rows[0]["data_date"], self.frames["AAA.IS"].index[-1].date().isoformat())

    def test_report_scores_matured_records(self):
        index = self.frames["AAA.IS"].index
        for i in (200, 210, 220):
            for symbol in ("AAA.IS", "BBB.IS"):
                log_signal("daily", symbol, 80, "Güçlü pozitif", index[i].date(), path=self.log)
        log_signal("analyze", "AAA.IS", 80, "Güçlü pozitif", index[230].date(), path=self.log)
        log_signal("daily", "AAA.IS", 80, "Güçlü pozitif", index[-1].date(), path=self.log)  # not matured

        scored = forward.score_log(self.log, bars=self.bars)
        text = forward.forward_report(self.log, self.equity, bars=self.bars)

        daily5 = scored[(scored["source"] == "daily") & (scored["horizon"] == 5)]
        self.assertEqual(len(daily5), 6)
        self.assertIn("5 seans:", text)
        self.assertIn("Güçlü pozitif", text)
        self.assertIn("6 kayıt, 3 gün", text)
        self.assertIn("henüz karar yok (3/20 gün)", text)
        self.assertIn("/top, /analyze ve /watchscan kayıtları: 1 olgun kayıt", text)

    def test_empty_log_and_paper(self):
        text = forward.forward_report(self.log, self.equity, bars=self.bars)

        self.assertIn("henüz olgunlaşmış kayıt yok", text)
        self.assertIn("Henüz yeterli kayıt yok", text)

    def test_paper_against_market(self):
        index = self.frames[BENCHMARK].index
        with open(self.equity, "w", encoding="utf-8", newline="") as fh:
            fh.write("date,account,value,cash,invested,positions\n")
            fh.write(f"{index[-10].date()},paper,100000,100000,0,0\n")
            fh.write(f"{index[-1].date()},paper,110000,10000,100000,1\n")

        stats = forward.paper_vs_market(self.equity, bars=self.bars)
        close = self.frames[BENCHMARK]["close"]

        self.assertAlmostEqual(stats.account, 0.10)
        self.assertAlmostEqual(stats.market, close.iloc[-1] / close.iloc[-10] - 1)
        self.assertEqual(stats.days, 2)


class WeeklyLineTest(RecordingAndReportTest):
    def test_empty(self):
        line = forward.weekly_line(self.log, self.equity, bars=self.bars)
        self.assertIn("kayıtlar birikiyor", line)
        self.assertNotIn("Sanal hesap", line)

    def test_with_matured_records_and_paper(self):
        index = self.frames["AAA.IS"].index
        for i in (200, 210, 220):
            log_signal("daily", "AAA.IS", 80, "Güçlü pozitif", index[i].date(), path=self.log)
        with open(self.equity, "w", encoding="utf-8", newline="") as fh:
            fh.write("date,account,value,cash,invested,positions\n")
            fh.write(f"{index[-10].date()},paper,100000,100000,0,0\n")
            fh.write(f"{index[-1].date()},paper,110000,10000,100000,1\n")

        line = forward.weekly_line(self.log, self.equity, bars=self.bars)
        self.assertIn("20 seans", line)
        self.assertIn("Güçlü pozitif", line)
        self.assertIn("3/20 gün", line)
        self.assertIn("Sanal hesap", line)


class DailyWeeklyTest(unittest.TestCase):
    def _text(self, day):
        from core.reports import daily

        with mock.patch.object(forward, "weekly_line", return_value="HAFTALIK"):
            return daily._with_weekly_line(f"rapor\n\n{daily.DISCLAIMER}", day)

    def test_only_on_fridays_and_before_disclaimer(self):
        from core.reports import daily

        friday = self._text(date(2026, 10, 30))
        self.assertLess(friday.index("HAFTALIK"), friday.index(daily.DISCLAIMER))
        self.assertNotIn("HAFTALIK", self._text(date(2026, 10, 29)))

    def test_failure_keeps_report(self):
        from core.reports import daily

        with mock.patch.object(forward, "weekly_line", side_effect=OSError("disk")):
            self.assertEqual(daily._with_weekly_line("rapor", date(2026, 10, 30)), "rapor")


class DailyRecordingTest(unittest.TestCase):
    def test_recording_failure_never_stops_the_report(self):
        from core.reports import daily

        with mock.patch.object(forward, "log_daily_scores", side_effect=OSError("disk")), \
                mock.patch.object(daily, "load_universe", return_value=["AAA.IS"]):
            daily._record_scores()  # must not raise

    def test_run_records_scores(self):
        from core.reports import daily

        fake = daily.DailyResult(date(2026, 10, 26), "rapor")
        args = mock.Mock(no_update=True, send=False)

        with mock.patch.object(daily, "build_daily", return_value=fake), \
                mock.patch.object(daily, "_record_scores") as record, \
                mock.patch.object(daily, "_with_backup_line", side_effect=lambda t: t):
            daily._run(args)

        record.assert_called_once()


if __name__ == "__main__":
    unittest.main()
