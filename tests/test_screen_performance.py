"""
/performans "Taramalar" (/tara Aşama 4c): each criterion's live result from the moment it was
recorded; under 30 matured samples it says "veri birikiyor" instead of a number. Always shown,
also before the first /tara.
"""

import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import pandas as pd

from core.reports import forward


def report(rows):
    tmp = tempfile.TemporaryDirectory()
    d = Path(tmp.name)
    with mock.patch.object(forward, "score_log", return_value=rows), \
            mock.patch.object(forward, "paper_vs_market", return_value=None):
        text = forward.forward_report(d / "s.csv", d / "e.csv", expectations_path=d / "x.csv")
    tmp.cleanup()
    return text


def rows(criterion, n, horizon):
    return [{"source": "tara", "view": criterion, "day": date(2026, 9, 1 + i % 28), "horizon": horizon,
             "excess": 0.01 * (i % 3 - 1), "symbol": f"S{i:02d}.IS"} for i in range(n)]


class TaramalarTest(unittest.TestCase):
    def test_always_present(self):
        empty = pd.DataFrame(columns=["source", "view", "day", "horizon", "excess", "symbol"])
        text = report(empty)
        self.assertIn("🔎 Taramalar", text)
        self.assertIn("veri birikiyor", text)

    def test_few_samples_show_no_number(self):
        text = report(pd.DataFrame(rows("rsi<30", 29, 5) + rows("rsi<30", 40, 20)))
        five = next(line for line in text.splitlines() if "rsi<30 · 5 seans" in line)
        self.assertIn("veri birikiyor (29/30 örnek)", five)
        self.assertNotIn("%", five)
        twenty = next(line for line in text.splitlines() if "rsi<30 · 20 seans" in line)
        self.assertIn("40 kayıt", twenty)
        self.assertIn("[", twenty)

    def test_criterion_hash_shown(self):
        from core.screen.command import criterion_hash

        text = report(pd.DataFrame(rows("rsi<30", 5, 5)))
        self.assertIn(criterion_hash("rsi<30"), text)


if __name__ == "__main__":
    unittest.main()
