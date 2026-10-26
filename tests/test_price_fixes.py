import tempfile
import unittest
from datetime import date
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
