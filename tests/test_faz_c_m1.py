"""
Faz C, M1 (the technical view score, docs/validation/M1.md). The score itself is unchanged (M1-4 is
left on purpose: changing it would restart the live measurement); what is said around it is fixed.

M1-3  /analyze names a close-to-close jump beyond a limit move (unrecorded corporate action)
M1-5  the daily score record uses the same 60-candle floor as /analyze
M1-8  /performans says its averages are before costs
M1-9  the trend line says it is not the score's definition
"""

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


def result(**kw):
    base = {"symbol": "THYAO.IS", "price": 259.0, "signal": "BUY", "score": 70, "trend": "BULLISH", "rsi": 55.0,
            "macd": 1.0, "volume_ratio": 1.0, "volatility": 0.02, "confidence": 25, "entry_price": 259.0,
            "stop_loss": 243.26, "target_1": 274.74, "target_2": 290.48, "ma20": 250.0, "ma50": 245.0}
    return base | kw


class AnalyzeTextTest(unittest.TestCase):
    def test_jump_warning_is_shown(self):
        from bot.analysis import _format_analysis

        text = _format_analysis(result(jump_warning=True))
        self.assertIn("kaydı eksik bir şirket işlemi", text)
        self.assertNotIn("kaydı eksik", _format_analysis(result()))

    def test_trend_line_names_its_definition(self):
        from bot.analysis import _format_analysis

        self.assertIn("EMA20/50/200; skordan ayrı tanım", _format_analysis(result()))

    def test_analyzer_flags_a_jump(self):
        from core.analytics import analyzer

        self.assertTrue(analyzer.has_jump(pd.Series([100.0] * 30 + [50.0] * 30)))
        self.assertFalse(analyzer.has_jump(pd.Series(100 + np.cumsum(np.full(60, 0.5)))))


class ShortHistoryTest(unittest.TestCase):
    def test_no_score_record_below_the_floor(self):
        from core.market.indicators import MIN_HISTORY_LENGTH
        from core.reports import forward

        rng = np.random.default_rng(0)
        c = 100 + np.cumsum(rng.normal(0, 1, MIN_HISTORY_LENGTH - 5))
        df = pd.DataFrame({"open": c, "high": c + 1, "low": c - 1, "close": c, "volume": 1e6},
                          index=pd.bdate_range("2026-07-01", periods=len(c)))
        with tempfile.TemporaryDirectory() as tmp:
            n = forward.log_daily_scores(["A.IS"], Path(tmp) / "log.csv", bars=lambda s: df)
        self.assertEqual(n, 0)


class CostWordingTest(unittest.TestCase):
    def test_performance_header_says_before_costs(self):
        import inspect

        from core.reports import forward

        self.assertTrue("maliyet öncesi" in inspect.getsource(forward), "the header does not say before costs")


if __name__ == "__main__":
    unittest.main()
