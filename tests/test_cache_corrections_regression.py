import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from core.market import corrections, data


class CacheCorrectionRegressionTest(unittest.TestCase):
    def test_price_fix_change_invalidates_cached_history(self):
        symbol = "CACHE_TEST.IS"
        idx = pd.date_range("2025-01-02", periods=3, freq="B")
        raw = pd.DataFrame(
            {
                "open": [100.0] * 3,
                "high": [110.0] * 3,
                "low": [90.0] * 3,
                "close": [100.0] * 3,
                "volume": [1000.0] * 3,
            },
            index=idx,
        )

        with tempfile.TemporaryDirectory() as temp:
            fixes = Path(temp) / "fixes.csv"
            fixes.write_text(
                f"symbol,date,factor\n{symbol},{idx[-1].date()},0.8\n",
                encoding="utf-8",
            )

            with (
                patch.object(data.store, "update", return_value={symbol: "ok"}),
                patch.object(data.store, "read", return_value=raw.copy()),
                patch.object(data, "drop_open_candle", side_effect=lambda df: df),
                patch.object(corrections, "load_corporate_actions", return_value=[]),
                patch.object(
                    corrections, '_validate_price_fix_source',
                    return_value=True
                ),
            ):
                data.clear_cache()
                corrections.use_price_fixes(None)
                try:
                    before = data.load_price_history(symbol, period="max")
                    corrections.use_price_fixes(fixes)
                    after = data.load_price_history(symbol, period="max")

                    self.assertAlmostEqual(before["close"].iloc[-1], 100.0)
                    self.assertAlmostEqual(after["close"].iloc[-1], 80.0)
                finally:
                    corrections.use_price_fixes(None)
                    data.clear_cache()
