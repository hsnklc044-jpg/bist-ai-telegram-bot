import unittest
from datetime import date
from unittest.mock import patch

import pandas as pd

from core.market import corrections, data
from core.market.corrections import CorporateAction


class CorporateActionCacheTest(unittest.TestCase):
    def test_corporate_action_change_invalidates_cache(self):
        symbol = "CACHE_ACTION.IS"
        idx = pd.to_datetime([
            "2025-01-02", "2025-01-03", "2025-01-06"
        ])
        # unadjusted raw data: the 0.8 action shows as a −20% ex-date gap (an already adjusted
        # history would be skipped, validation M15)
        raw = pd.DataFrame({
            "open": [100., 100., 80.],
            "high": [110., 110., 88.],
            "low": [90., 90., 72.],
            "close": [100., 100., 80.],
            "volume": [1000.] * 3,
        }, index=idx)

        action = CorporateAction(
            symbol, date(2025, 1, 6),
            factor=0.8, source="test"
        )

        with patch.object(
            data.store, "update",
            return_value={symbol: "ok"}
        ), patch.object(
            data.store, "read",
            return_value=raw.copy()
        ), patch.object(
            data, "drop_open_candle",
            side_effect=lambda df: df
        ), patch.object(
            corrections, "load_corporate_actions",
            return_value=[]
        ):
            corrections.use_corporate_actions(None)
            data.clear_cache()
            try:
                before = data.load_price_history(
                    symbol, period="max"
                )

                corrections.use_corporate_actions([action])
                after = data.load_price_history(
                    symbol, period="max"
                )

                self.assertAlmostEqual(
                    before["close"].iloc[0], 100.
                )
                self.assertAlmostEqual(
                    after["close"].iloc[0], 80.
                )
                self.assertAlmostEqual(
                    after["close"].iloc[-1], 80.
                )
            finally:
                corrections.use_corporate_actions(None)
                data.clear_cache()
