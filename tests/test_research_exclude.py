"""CHARTER C1: stocks the second source marked as suspect can be left out of a research run."""

import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from core.backtest import research


class ExcludeSuspectsTest(unittest.TestCase):
    def test_suspects_are_dropped_from_frames_and_eligibility(self):
        index = pd.bdate_range("2026-01-01", periods=3)
        frames = {s: pd.DataFrame({"close": [1.0, 2.0, 3.0]}, index=index) for s in ("AAA.IS", "BBB.IS", "CCC.IS")}
        eligible = pd.DataFrame(True, index=index, columns=list(frames))
        kept, kept_eligible, dropped = research.drop_suspects(frames, eligible, {"BBB"})
        self.assertEqual(sorted(kept), ["AAA.IS", "CCC.IS"])
        self.assertEqual(list(kept_eligible.columns), ["AAA.IS", "CCC.IS"])
        self.assertEqual(dropped, ["BBB.IS"])

    def test_suspects_are_read_from_the_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "latest.json"
            path.write_text(json.dumps({"date": "2026-10-31", "checked": 100, "differing": ["BBB", "DDD"],
                                        "unchecked": [], "share": 0.02}), encoding="utf-8")
            self.assertEqual(research.load_suspects(path), {"BBB", "DDD"})


if __name__ == "__main__":
    unittest.main()
