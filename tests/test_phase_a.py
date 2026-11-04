"""
Faz A of the work plan (docs/ROADMAP.md "Eksiksiz iş planı"): findings of the independent validation
that are plain bugs and change no measurement rule. One test per finding, named after it.
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd


class Batch1Test(unittest.TestCase):
    def test_m27_5_risk_limits_match_the_message(self):
        from core.analytics.scenarios import parse_args

        with self.assertRaisesRegex(ValueError, "%0,1 ile %5"):
            parse_args(["THYAO", "risk=%0,05"])  # 0,05% is below the stated 0,1%
        self.assertAlmostEqual(parse_args(["THYAO", "risk=%0,1"])[2], 0.001)

    def test_m27_7_size_line_says_costs_and_gaps_are_out(self):
        from core.analytics import scenarios

        df = pd.DataFrame({"close": [100.0] * 30, "volume": [1e6] * 30})
        self.assertIn("maliyet ve boşluk hariç", scenarios.size(100.0, 95.0, 100_000, 0.01, df))

    def test_m8_4_round_numbers_on_a_bad_close(self):
        from core.analytics.levels import round_numbers

        self.assertEqual(round_numbers(0.0), ())
        self.assertEqual(round_numbers(float("nan")), ())
        self.assertEqual(round_numbers(270.0), (250.0, 300.0))

    def test_m30_8_goreli20_needs_the_index(self):
        from core.ml import features

        df = pd.DataFrame({"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1.0},
                          index=pd.bdate_range("2024-01-01", periods=300))
        with self.assertRaisesRegex(ValueError, "XU100"):
            features.dataset({"A.IS": df}, rule="goreli20")

    def test_m31_9_broken_report_files(self):
        from core.ml import signal_filter as S

        with tempfile.TemporaryDirectory() as tmp:
            for body in ("null", "[]", '"x"'):
                p = Path(tmp) / "r.json"
                p.write_text(body, encoding="utf-8")
                with mock.patch.object(S, "report_file", return_value=p):
                    self.assertFalse(S.validated("gunluk"))
                    self.assertEqual(S.track_record("gunluk"), S.RECORDED["gunluk"])
