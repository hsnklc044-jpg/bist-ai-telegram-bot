"""yfinance's own pandas deprecation warnings (Pandas4Warning) are silenced; ours are not (open item 05.11.2026)."""

import unittest
import warnings

from pandas.errors import Pandas4Warning

from core.infrastructure.logger import quiet_yfinance


class QuietYfinanceTest(unittest.TestCase):
    def test_library_warning_hidden_ours_shown(self):
        with warnings.catch_warnings(record=True) as seen:
            warnings.simplefilter("always")
            quiet_yfinance()
            warnings.warn_explicit("inplace is deprecated", Pandas4Warning, "base.py", 716, module="yfinance.base")
            warnings.warn_explicit("ours", Pandas4Warning, "x.py", 1, module="core.market.provider")
        self.assertEqual([str(w.message) for w in seen], ["ours"])

    def test_survives_yfinance_reimport_filter(self):
        with warnings.catch_warnings(record=True) as seen:
            warnings.simplefilter("always")
            quiet_yfinance()
            warnings.filterwarnings("default", category=DeprecationWarning, module="^yfinance")  # what yf adds
            quiet_yfinance()
            warnings.warn_explicit("inplace", Pandas4Warning, "base.py", 1, module="yfinance.base")
        self.assertEqual(seen, [])


if __name__ == "__main__":
    unittest.main()
