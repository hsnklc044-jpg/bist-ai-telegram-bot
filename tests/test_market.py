import unittest

from core.market.indicators import generate_indicator_snapshot
from core.market.models import MarketTrend
from tests.helpers import offline_market


class IndicatorTest(unittest.TestCase):
    def test_snapshot_values_are_sane(self):
        with offline_market():
            snap = generate_indicator_snapshot("THYAO.IS")

        self.assertGreater(snap.price, 0)
        self.assertTrue(0 <= snap.rsi <= 100)
        self.assertGreater(snap.atr, 0)
        self.assertLess(snap.bollinger_lower, snap.bollinger_upper)
        self.assertIsInstance(snap.trend, MarketTrend)

    def test_analyze_stock_trade_levels(self):
        from core.analytics.analyzer import analyze_stock

        with offline_market():
            result = analyze_stock("EREGL.IS")

        self.assertIsNotNone(result)
        self.assertLess(result["stop_loss"], result["entry_price"])
        self.assertLess(result["entry_price"], result["target_1"])
        self.assertLess(result["target_1"], result["target_2"])
