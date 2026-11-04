"""
Faz A of the work plan (docs/ROADMAP.md "Eksiksiz iş planı"): findings of the independent validation
that are plain bugs and change no measurement rule. One test per finding, named after it.
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
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


class Batch2Test(unittest.TestCase):
    def test_m30_4_only_the_live_filters_own_pass_counts(self):
        from core.ml import ml_filter

        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "r.json"

            def write(**kw):
                import json as js

                p.write_text(js.dumps({"passed": True, "universe": "BIST 30 yaklaşığı", "rule": "stop_hedef",
                                       "holdout_used": False} | kw), encoding="utf-8")

            write()
            self.assertTrue(ml_filter.enabled(p))
            for bad in ({"universe": "BIST 100"}, {"rule": "goreli20"}, {"holdout_used": True}):
                write(**bad)
                self.assertFalse(ml_filter.enabled(p), bad)
        self.assertNotEqual(ml_filter.report_path("bist100", "stop_hedef"), ml_filter.REPORT_FILE)
        self.assertEqual(ml_filter.report_path("bist30", "stop_hedef"), ml_filter.REPORT_FILE)

    def test_m30_10_tara_ml_reads_the_model_gate(self):
        from core.reports import model_gate
        from core.screen import engine

        result = engine.Result(query=None, day=None, matches=[object()])
        with mock.patch("core.ml.ml_filter.load", return_value={"passed": True}), \
                mock.patch.object(model_gate, "decide", return_value=model_gate.Decision("M30", False, "kullanılamaz")):
            engine._ml_filter(result, {})
        self.assertEqual(result.matches, [])
        self.assertIn("model kapısı", result.ml_note)

    def test_m31_13_an_old_live_model_is_retrained(self):
        from datetime import date

        from core.screen import ai

        old = {"model": object(), "trained": "2026-10-01"}
        with mock.patch("core.ml.signal_filter.load_live", side_effect=[old, {"model": None, "trained": "2026-11-04"}]), \
                mock.patch("core.ml.signal_filter._daily", return_value=({}, None)), \
                mock.patch("core.ml.signal_filter.fit_live") as fit, \
                mock.patch.object(ai, "run", return_value=[]), \
                mock.patch("core.reports.daily.adjusted_bars", return_value=pd.DataFrame()):
            ai.live(date(2026, 11, 4))
        fit.assert_called_once()

    def test_m32_10_risk_is_rewritten_at_the_entry(self):
        from datetime import date

        from core.signals import panic
        from core.signals import store as S

        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(panic, "PANIC_FILE", Path(tmp) / "p.lock"):
            conn = S.connect(Path(tmp) / "b.db")
            try:
                S.add(conn, date(2026, 11, 2), "A.IS", 100.0, qty=100)  # risk at the card: 100 × 100 × 2% = 200
                idx = pd.bdate_range("2026-11-02", periods=2)
                df = pd.DataFrame({"open": [100.0, 90.0], "high": [100.0, 91.0], "low": [100.0, 89.5],
                                   "close": [100.0, 90.5]}, index=idx)  # a gap: entry at 90
                S.update(conn, lambda s: df)
                row = conn.execute("SELECT risk_tl FROM signals").fetchone()
            finally:
                conn.close()
        self.assertAlmostEqual(row["risk_tl"], 100 * 90.0 * S.STOP)  # 180 at the real entry


class Batch3Test(unittest.TestCase):
    def test_m30_7_a_nan_close_at_the_horizon_has_no_label(self):
        from core.ml import features

        rows = [(100, 100, 100, 100)] * 2 + [(100, 101, 99.5, 100)] * 9 + [(100, 101, 99.5, float("nan"))]
        df = pd.DataFrame(rows, columns=["open", "high", "low", "close"],
                          index=pd.bdate_range("2026-01-01", periods=len(rows)))
        got = features.labels(df, horizon=10)
        self.assertTrue(np.isnan(got["label"].iloc[1]))  # row 1 ends on the NaN close: no label, not a 0
        self.assertEqual(got["label"].iloc[0], 0.0)  # row 0 ends on a real close

    def test_m1_7_atr_levels_are_rounded_after_multiplying(self):
        from core.analytics import analyzer

        src = Path(analyzer.__file__).read_text(encoding="utf-8")
        self.assertIn("snapshot.price - snapshot.atr * 2", src)  # 1,50 TL, ATR 0,034: stop 1,43 not 1,44

    def test_m5_6_no_index_is_said(self):
        from core.screen import card
        from core.screen.language import parse
        from tests.test_screen_card import flat

        stats = card.history(parse("kapanis>0"), {"A.IS": flat()}, flat().iloc[0:0], horizons=(5,))[5]
        self.assertIn("XU100 verisi yok", stats.label)

    def test_m8_7_level_fields_carry_the_study_note(self):
        from core.screen.fields import FIELDS

        for name in ("destek_uzaklik_atr", "direnc_uzaklik_atr", "seviye_gucu"):
            self.assertIn("rastgele", FIELDS[name].text, name)
