"""
K-22 / docs/RESEARCH_PROGRAM.md: from 02.11.2026 prices are the holdout. No screening tool
(research, phase3, candidates, ...) may see them; they all load prices through load_frames.
The daily report and the live measurement read the store directly and are not cut.
"""

import unittest
from unittest import mock

import pandas as pd

from core.backtest import run
from tests.helpers import make_ohlcv


class HoldoutNeverEntersScreeningTest(unittest.TestCase):
    def test_screening_data_ends_before_the_holdout(self):
        df = make_ohlcv(400, end="2027-01-15")  # runs past 02.11.2026
        self.assertGreater(df.index[-1], pd.Timestamp("2026-11-02"))
        with mock.patch.object(run.store, "read", return_value=df), \
                mock.patch.object(run, "clean", side_effect=lambda d, s: d), \
                mock.patch.object(run, "drop_open_candle", side_effect=lambda d: d):
            frames = run.load_frames(["AAA.IS"])
            opened = run.load_frames(["AAA.IS"], include_holdout=True)
        self.assertLessEqual(frames["AAA.IS"].index[-1], run.SCREEN_END)
        self.assertLess(run.SCREEN_END, run.HOLDOUT_START)
        self.assertEqual(run.HOLDOUT_START, pd.Timestamp("2026-11-02"))
        self.assertEqual(opened["AAA.IS"].index[-1], df.index[-1])  # only an explicit holdout verdict sees it

    def test_the_documents_name_the_same_dates(self):
        from pathlib import Path

        text = (Path(__file__).resolve().parents[1] / "docs" / "RESEARCH_PROGRAM.md").read_text(encoding="utf-8")
        self.assertIn(f"{run.HOLDOUT_START:%d.%m.%Y}", text)
        self.assertIn(f"{run.SCREEN_END:%d.%m.%Y}", text)


if __name__ == "__main__":
    unittest.main()
