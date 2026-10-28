"""
Özellik A §2.4, §2.5, §3.4: the daily report shows the nearest support under each open position
as an information line (the ATR trailing-stop warning is unchanged); after the report the levels
are written, before the outcome is known, to logs/levels_log.csv (append-only); /durum shows the
last levels day.
"""

import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

from core.analytics import levels as L
from core.ledger import Entry, append_entry
from core.market import store
from core.market.calendar import ISTANBUL
from core.market.universe import BENCHMARK
from core.reports import health
from core.reports.daily import Paths, build_daily
from tests.helpers import offline_market
from tests.test_levels import market

UNIVERSE = ["AAA.IS", "BBB.IS", "CCC.IS"]
NOW = datetime(2026, 10, 24, 12, 0, tzinfo=ISTANBUL)


class ReportLineTest(unittest.TestCase):
    def test_position_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            paths = Paths(d / "ledger.csv", d / "orders.csv", d / "alerts.csv", d / "equity.csv")
            append_entry(Entry(date(2026, 6, 1), "real", "AAA", "buy", 100, 50.0, 5.0), paths.ledger)
            with offline_market():
                store.update([BENCHMARK, *UNIVERSE], now=NOW)
                text = build_daily(paths, UNIVERSE).text
        line = next(x for x in text.splitlines() if "en yakın destek" in x)
        self.assertIn("teknik seviye, öneri değil", line)
        self.assertIn("ATR", line)

    def test_support_line_for_one_stock(self):
        line = L.position_line(market())
        self.assertIn("en yakın destek", line)
        self.assertIn("küme", line)
        self.assertEqual(L.position_line(market(10)), "")


class LogTest(unittest.TestCase):
    def test_append_only_once_per_day_and_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "levels_log.csv"
            frames = {"AAA.IS": market(seed=1), "BBB.IS": market(seed=2)}
            day = frames["AAA.IS"].index[-1].date()
            written = L.write_log(day, frames, path=path, now=NOW)
            self.assertGreater(written, 0)
            before = path.read_text(encoding="utf-8")
            self.assertEqual(L.write_log(day, frames, path=path, now=NOW), 0)  # the same day is not written twice
            self.assertEqual(path.read_text(encoding="utf-8"), before)
            header = before.splitlines()[0].split(",")
            self.assertEqual(header, list(L.LOG_COLUMNS))
            rows = before.splitlines()[1:]
            self.assertTrue(all(r.split(",")[2] == "küme" for r in rows))
            self.assertEqual(L.last_log_day(path), day)
            check = health.levels_check(path, now=datetime.combine(day, datetime.min.time(), ISTANBUL).replace(hour=20))
            self.assertIn(f"{day:%d.%m.%Y}", check.text)
            self.assertEqual(health.levels_check(Path(tmp) / "none.csv").state, health.UNKNOWN)

    def test_wired_into_status_and_the_report(self):
        from core.reports import daily

        self.assertIn("Seviye hesabı", [c.name for c in health.health_checks()])
        self.assertTrue(hasattr(daily, "_record_levels"))


if __name__ == "__main__":
    unittest.main()
