"""scripts/kart_modeli_kontrol.py (K-79, A1.3-A1.4): the Friday check of the live /tara ai model."""

import importlib.util
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date
from io import StringIO
from pathlib import Path
from unittest import mock

import pandas as pd

PATH = Path(__file__).resolve().parents[1] / "scripts" / "kart_modeli_kontrol.py"
spec = importlib.util.spec_from_file_location("kart_modeli_kontrol", PATH)
K = importlib.util.module_from_spec(spec)
spec.loader.exec_module(K)


class Card:
    def __init__(self, id, created):
        self.id, self.created, self.symbol, self.status = id, created, "THYAO.IS", "onay_bekliyor"


class CheckTest(unittest.TestCase):
    def run_check(self, trained, rows, expected, last_end, cards):
        from core.ml import signal_filter as S

        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(K, "MARK_FILE", Path(tmp) / "isaret.csv"), \
                mock.patch.object(S, "load_live", return_value={"trained": trained, "rows": rows}), \
                mock.patch.object(K, "expected_rows", return_value=(expected, last_end)), \
                mock.patch.object(K, "cards_between", return_value=cards), redirect_stdout(StringIO()) as out:
            code = K.main()
            marks = (Path(tmp) / "isaret.csv").read_text(encoding="utf-8") if (Path(tmp) / "isaret.csv").exists() else ""
        return code, out.getvalue(), marks

    def test_friday_model_under_the_new_rule(self):
        code, text, marks = self.run_check("2026-11-06", 700, 700, pd.Timestamp("2026-10-30"), [Card(5, date(2026, 11, 4))])
        self.assertEqual(code, 0, text)
        self.assertIn("SONUÇ: DOĞRULANDI", text)
        self.assertIn("holdout etkisi olabilir", marks)

    def test_old_model_or_mismatch_is_not_verified(self):
        self.assertEqual(self.run_check("2026-11-03", 744, 700, pd.Timestamp("2026-10-30"), [])[0], 1)
        self.assertEqual(self.run_check("2026-11-06", 744, 700, pd.Timestamp("2026-10-30"), [])[0], 1)
        self.assertEqual(self.run_check("2026-11-06", 700, 700, pd.Timestamp("2026-11-02"), [])[0], 1)

    def test_installed_fit_live_is_the_frozen_one(self):
        self.assertTrue(K.frozen_fit_live())

    def test_marks_are_not_repeated(self):
        cards = [Card(5, date(2026, 11, 4))]
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(K, "MARK_FILE", Path(tmp) / "m.csv"):
            self.assertEqual(K.mark(cards, pd.Timestamp("2026-11-06").to_pydatetime()), 1)
            self.assertEqual(K.mark(cards, pd.Timestamp("2026-11-06").to_pydatetime()), 0)


if __name__ == "__main__":
    unittest.main()
