"""Friday report trend line (K-25): a text sparkline of the paper account and XU100 over the last
sessions, in the same message (no image library, no second send)."""

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from core.market.universe import BENCHMARK
from core.reports import forward


class SparklineTest(unittest.TestCase):
    def test_lowest_and_highest_get_the_extreme_bars(self):
        self.assertEqual(forward.sparkline([1, 2, 3, 4, 5, 6, 7, 8]), "▁▂▃▄▅▆▇█")
        self.assertEqual(forward.sparkline([5, 5, 5]), "▄▄▄")  # flat: middle bars, no division by zero
        self.assertEqual(forward.sparkline([]), "")


class WeeklyChartTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "equity.csv"
        days = pd.bdate_range("2026-09-01", periods=30)
        rows = ["date,account,value,cash,invested,positions"]
        rows += [f"{d.date()},paper,{100000 + 100 * i},50000,{50000 + 100 * i},1" for i, d in enumerate(days)]
        self.path.write_text("\n".join(rows) + "\n", encoding="utf-8")
        xu = pd.DataFrame({"close": [10000 - 10 * i for i in range(30)]}, index=days)
        self.bars = lambda s: xu if s == BENCHMARK else pd.DataFrame()

    def test_last_sessions_of_account_and_market_side_by_side(self):
        line = forward.weekly_chart(self.path, bars=self.bars, sessions=20)
        self.assertIn("Son 20 seans", line)
        self.assertIn("Sanal hesap ▁", line)   # rising: starts low
        self.assertIn("█ +%", line)
        self.assertIn("XU100 █", line)          # falling: starts high
        self.assertIn("▁ -%", line)

    def test_too_few_records_means_no_line(self):
        self.path.write_text("date,account,value,cash,invested,positions\n2026-10-01,paper,100000,0,0,0\n",
                             encoding="utf-8")
        self.assertEqual(forward.weekly_chart(self.path, bars=self.bars), "")

    def test_friday_line_includes_it(self):
        text = forward.weekly_line(signal_path=self.path.parent / "yok.csv", equity_path=self.path, bars=self.bars)
        self.assertIn("📈 Son", text)


if __name__ == "__main__":
    unittest.main()
