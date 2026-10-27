import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

from core.market import corrections


class CentralPriceFixGateTest(unittest.TestCase):

    def tearDown(self):
        corrections.use_price_fixes(None)

    def test_rejected_csv_does_not_change_state(self):
        corrections.use_price_fixes(None)
        with tempfile.TemporaryDirectory() as folder:
            candidate = Path(folder) / "fixes.csv"
            candidate.write_text('symbol,date,factor\nTEST.IS,2025-01-02,0.95\n', encoding="utf-8")
            with mock.patch.object(
                corrections, "_validate_price_fix_source",
                side_effect=ValueError("ENGELLENDI")
            ):
                with self.assertRaisesRegex(ValueError, "ENGELLENDI"):
                    corrections.use_price_fixes(candidate)
            self.assertIsNone(corrections._price_fixes)

    def test_disable_does_not_validate(self):
        with mock.patch.object(
            corrections, "_validate_price_fix_source"
        ) as validator:
            self.assertEqual(corrections.use_price_fixes(None), 0)
            validator.assert_not_called()

    def test_approved_fixture_loads_one_record(self):
        with tempfile.TemporaryDirectory() as folder:
            candidate = Path(folder) / "fixes.csv"
            candidate.write_text('symbol,date,factor\nTEST.IS,2025-01-02,0.95\n', encoding="utf-8")
            with mock.patch.object(
                corrections, "_validate_price_fix_source",
                return_value=True
            ) as validator:
                self.assertEqual(corrections.use_price_fixes(candidate), 1)
                validator.assert_called_once()
                snapshot_path = Path(validator.call_args.args[0])
                self.assertNotEqual(snapshot_path, candidate)
                self.assertEqual(
                    snapshot_path.name, "verified_fixes.csv"
                )


    def test_original_csv_change_cannot_change_loaded_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            candidate = Path(folder) / "fixes.csv"
            original_csv = (
                "symbol,date,factor\n"
                "TEST.IS,2025-01-02,0.95\n"
            )
            altered_csv = (
                "symbol,date,factor\n"
                "TEST.IS,2025-01-02,1.25\n"
            )
            candidate.write_text(original_csv, encoding="utf-8")

            def modify_original(snapshot):
                candidate.write_text(altered_csv, encoding="utf-8")
                self.assertEqual(
                    Path(snapshot).read_text(encoding="utf-8"),
                    original_csv
                )
                return True

            with mock.patch.object(
                corrections, "_validate_price_fix_source",
                side_effect=modify_original
            ):
                self.assertEqual(
                    corrections.use_price_fixes(candidate), 1
                )

            factor = corrections._price_fixes["TEST.IS"][
                pd.Timestamp("2025-01-02")
            ]
            self.assertAlmostEqual(factor, 0.95)

    def test_validation_failure_preserves_previous_state(self):
        with tempfile.TemporaryDirectory() as folder:
            candidate = Path(folder) / "fixes.csv"
            candidate.write_text(
                "symbol,date,factor\n"
                "TEST.IS,2025-01-02,0.95\n",
                encoding="utf-8"
            )

            with mock.patch.object(
                corrections, "_validate_price_fix_source",
                return_value=True
            ):
                corrections.use_price_fixes(candidate)

            before = corrections._price_fixes

            with mock.patch.object(
                corrections, "_validate_price_fix_source",
                side_effect=ValueError("ENGELLENDI")
            ):
                with self.assertRaisesRegex(ValueError, "ENGELLENDI"):
                    corrections.use_price_fixes(candidate)

            self.assertIs(corrections._price_fixes, before)


if __name__ == "__main__":
    unittest.main()
