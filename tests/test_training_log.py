"""
Every live /tara ai model training is recorded (open item from 05.11.2026: a retrain by /tara ai left no
trace, so a card could not be tied to the model that scored it). Both trainers write one row:
the Friday refit (core.reports.daily) and the stale/missing-model retrain (core.screen.ai).
"""

import csv
import unittest
from datetime import date
from unittest import mock

import pandas as pd

from core.ml import training_log


def rows():
    with open(training_log.LOG_FILE, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


class TrainingLogTest(unittest.TestCase):
    def test_record_appends_with_header(self):
        training_log.record(date(2026, 11, 6), "cuma", "haftalık", 812)
        training_log.record(date(2026, 11, 9), "tara-ai", "model yok", 0)
        got = rows()
        self.assertEqual([r["kaynak"] for r in got], ["cuma", "tara-ai"])
        self.assertEqual(got[0]["gun"], "2026-11-06")
        self.assertEqual(got[0]["satir"], "812")
        self.assertEqual(got[1]["neden"], "model yok")
        self.assertIn("surum", got[0])

    def test_a_write_failure_never_breaks_training(self):
        with mock.patch("builtins.open", side_effect=OSError("disk")):
            training_log.record(date(2026, 11, 6), "cuma", "haftalık", 1)

    def test_tara_ai_retrain_is_recorded(self):
        from core.ml import signal_filter as S
        from core.screen import ai

        old = {"model": None, "trained": "2026-10-01", "rows": 1, "params": {}}
        with mock.patch.object(S, "load_live", return_value=old), \
                mock.patch.object(S, "_daily", return_value=({}, None)), \
                mock.patch.object(S, "fit_live", return_value=744), \
                mock.patch.object(S, "validated", return_value=False), \
                mock.patch("core.reports.daily.adjusted_bars", side_effect=lambda s: pd.DataFrame()):
            ai.live(date(2026, 11, 5))
        got = rows()
        self.assertEqual(len(got), 1)
        self.assertEqual((got[0]["kaynak"], got[0]["satir"]), ("tara-ai", "744"))
        self.assertIn("eski", got[0]["neden"])

    def test_fresh_model_writes_nothing(self):
        from core.ml import signal_filter as S
        from core.screen import ai

        fresh = {"model": None, "trained": "2026-11-03", "rows": 744, "params": {}}
        with mock.patch.object(S, "load_live", return_value=fresh), \
                mock.patch.object(S, "validated", return_value=False), \
                mock.patch("core.reports.daily.adjusted_bars", side_effect=lambda s: pd.DataFrame()):
            ai.live(date(2026, 11, 5))
        self.assertFalse(training_log.LOG_FILE.exists())

    def test_friday_refit_is_recorded(self):
        from core.ml import signal_filter as S
        from core.reports import daily

        with mock.patch.object(S, "_daily", return_value=({}, None)), \
                mock.patch.object(S, "fit_live", return_value=812):
            daily._refit_signal_model(date(2026, 11, 6))
            daily._refit_signal_model(date(2026, 11, 5))  # not a Friday: nothing
        got = rows()
        self.assertEqual([(r["kaynak"], r["gun"], r["satir"]) for r in got], [("cuma", "2026-11-06", "812")])


if __name__ == "__main__":
    unittest.main()
