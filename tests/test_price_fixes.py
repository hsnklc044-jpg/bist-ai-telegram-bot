import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import pandas as pd

from core.market import corrections, crosscheck


def frame(closes, start="2026-10-12"):
    index = pd.bdate_range(start, periods=len(closes))
    c = pd.Series(closes, index=index, dtype=float)
    return pd.DataFrame({"open": c, "high": c, "low": c, "close": c, "volume": 1e6})


class PriceFixesTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "price_fixes.csv"
        self.addCleanup(corrections.use_price_fixes, None)
        validator = mock.patch.object(corrections, "_validate_price_fix_source", return_value=True)
        validator.start()
        self.addCleanup(validator.stop)

    def test_fix_makes_the_stored_close_right(self):
        theirs = frame([100.0, 90.0, 94.0, 95.0, 96.0, 97.0])
        ours = theirs.copy()
        ours.loc[ours.index[1], "close"] = 96.0  # wrong close on 13.10

        result = crosscheck.compare("GARAN.IS", ours, theirs[["close"]])
        self.assertEqual(result.close_errors, [date(2026, 10, 13)])
        (day, factor), = result.fixes
        self.assertAlmostEqual(96.0 * factor, 90.0)

        self.assertEqual(crosscheck.export_fixes([result], self.path), 1)
        self.assertEqual(corrections.use_price_fixes(self.path), 1)
        fixed = corrections.clean(ours, "GARAN.IS", actions=[])
        self.assertAlmostEqual(fixed.loc[pd.Timestamp(day), "close"], 90.0)
        self.assertLessEqual(fixed.loc[pd.Timestamp(day), "low"], 90.0)  # candle stays consistent

    def test_off_by_default(self):
        ours = frame([100.0, 96.0, 94.0])
        self.path.write_text("symbol,date,factor,source,note\nGARAN.IS,2026-10-13,0.9375,x,y\n", encoding="utf-8")
        self.assertTrue(corrections.clean(ours, "GARAN.IS", actions=[]).equals(ours))

        corrections.use_price_fixes(self.path)
        self.assertAlmostEqual(corrections.clean(ours, "GARAN.IS", actions=[])["close"].iloc[1], 90.0)
        self.assertTrue(corrections.clean(ours, "THYAO.IS", actions=[]).equals(ours))  # other stocks untouched

        corrections.use_price_fixes(None)
        self.assertTrue(corrections.clean(ours, "GARAN.IS", actions=[]).equals(ours))

    def test_implausible_factor_refused(self):
        self.path.write_text("symbol,date,factor,source,note\nX.IS,2026-10-13,3.0,x,y\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            corrections.use_price_fixes(self.path)



class ApprovalGateTest(unittest.TestCase):
    """The real gate: a one-day fix is used only if data/price_fix_approvals.csv approves that row, with a source."""

    HEADER = "symbol,date,factor,approved,source,note\n"

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.fixes = self.dir / "fixes.csv"
        self.fixes.write_text("symbol,date,factor,source,note\nTEST.IS,2025-01-02,0.950000,isyatirim,x\n",
                              encoding="utf-8")
        self.addCleanup(corrections.use_price_fixes, None)

    def approvals(self, rows: str) -> Path:
        path = self.dir / "approvals.csv"
        path.write_text(self.HEADER + rows, encoding="utf-8")
        return path

    def check(self, rows):
        return corrections._validate_price_fix_source(self.fixes, approvals=self.approvals(rows))

    def test_approved_row_passes(self):
        self.assertTrue(self.check("TEST.IS,2025-01-02,0.95,true,İş Yatırım + KAP,elle doğrulandı\n"))

    def test_unapproved_row_is_blocked(self):
        with self.assertRaisesRegex(corrections.PriceFixGateError, "1 onaysız"):
            self.check("TEST.IS,2025-01-02,0.95,false,İş Yatırım,inceleniyor\n")

    def test_row_missing_from_the_list_is_blocked(self):
        with self.assertRaisesRegex(corrections.PriceFixGateError, "onay listesinde yok"):
            self.check("OTHER.IS,2025-01-02,0.95,true,İş Yatırım,x\n")

    def test_different_factor_is_blocked(self):
        with self.assertRaisesRegex(corrections.PriceFixGateError, "çarpan"):
            self.check("TEST.IS,2025-01-02,0.90,true,İş Yatırım,x\n")

    def test_approval_without_a_source_is_refused(self):
        with self.assertRaisesRegex(corrections.PriceFixGateError, "kaynağı yok"):
            self.check("TEST.IS,2025-01-02,0.95,true,,x\n")

    def test_duplicate_rows_are_refused(self):
        with self.assertRaisesRegex(corrections.PriceFixGateError, "tekrar"):
            self.check("TEST.IS,2025-01-02,0.95,true,a,x\nTEST.IS,2025-01-02,0.95,true,a,x\n")

    def test_use_price_fixes_goes_through_the_gate(self):
        with mock.patch.object(corrections, "APPROVALS_FILE", self.approvals("")):
            with self.assertRaises(corrections.PriceFixGateError):
                corrections.use_price_fixes(self.fixes)
        self.assertIsNone(corrections._price_fixes)
        with mock.patch.object(corrections, "APPROVALS_FILE",
                               self.approvals("TEST.IS,2025-01-02,0.95,true,İş Yatırım + KAP,x\n")):
            self.assertEqual(corrections.use_price_fixes(self.fixes), 1)

    def test_research_stops_with_a_clear_line_when_blocked(self):
        import contextlib
        import io

        from core.backtest import research

        out = io.StringIO()
        with mock.patch.object(corrections, "APPROVALS_FILE", self.approvals("")), \
                mock.patch.object(research, "research_report") as report, contextlib.redirect_stdout(out):
            research.main(["--price-fixes", str(self.fixes)])
        report.assert_not_called()  # nothing is measured with unapproved fixes
        self.assertIn("Fiyat düzeltmeleri uygulanmadı: ENGELLENDİ", out.getvalue())

    def test_scenarios_drop_blocked_fixes(self):
        from core.backtest import scenarios

        with mock.patch.object(corrections, "APPROVALS_FILE", self.approvals("")):
            path, line = scenarios._approved_fixes(self.fixes)
        self.assertIsNone(path)
        self.assertIn("C ve D çalıştırılmadı", line)
        ok = self.approvals("TEST.IS,2025-01-02,0.95,true,İş Yatırım + KAP,x\n")
        with mock.patch.object(corrections, "APPROVALS_FILE", ok):
            self.assertEqual(scenarios._approved_fixes(self.fixes), (self.fixes, None))

    def test_committed_list_approves_nothing_yet(self):
        """User decision 27.10: one-day close fixes stay off; the committed list has no approved row."""

        with open(corrections.APPROVALS_FILE, encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        self.assertFalse([r for r in rows if r["approved"].strip().lower() == "true"])


if __name__ == "__main__":
    unittest.main()