import math
import unittest

import pandas as pd

from core.backtest.engine import BacktestConfig, Trade, run_backtest
from core.backtest.reliability import (
    contribution,
    market_regime,
    regime_breakdown,
    reliability_report,
    trade_stats,
    yearly_returns,
)
from core.strategy.rules import apply_rule, trend_rule
from tests.golden import load_prices
from tests.test_backtest import always, frame

T = pd.Timestamp


def trade(symbol, entry, exit_, shares=10.0):
    return Trade(symbol, T("2026-01-05"), entry, T("2026-01-09"), exit_, "signal", shares)


class TradeStatsTest(unittest.TestCase):
    def test_hand_computed(self):
        trades = [trade("A", 100, 110), trade("B", 100, 95), trade("C", 50, 60, shares=20)]
        st = trade_stats(trades)
        # returns: +10%, -5%, +20%
        self.assertAlmostEqual(st["expectancy"], (0.10 - 0.05 + 0.20) / 3)
        self.assertAlmostEqual(st["win_rate"], 2 / 3)
        self.assertAlmostEqual(st["avg_win"], 0.15)
        self.assertAlmostEqual(st["avg_loss"], -0.05)
        self.assertAlmostEqual(st["payoff_ratio"], 3.0)
        # profit 10*10 + 20*10 = 300, loss 10*5 = 50
        self.assertAlmostEqual(st["profit_factor"], 6.0)

    def test_no_trades(self):
        self.assertEqual(trade_stats([]), {"trades": 0})


class YearlyTest(unittest.TestCase):
    def test_years_chain(self):
        eq = pd.Series(
            [100, 110, 121, 133.1],
            index=[T("2024-03-01"), T("2024-12-31"), T("2025-12-31"), T("2026-06-30")],
        )
        y = yearly_returns(eq)
        self.assertAlmostEqual(y[2024], 0.10)
        self.assertAlmostEqual(y[2025], 0.10)
        self.assertAlmostEqual(y[2026], 0.10)
        self.assertAlmostEqual((1 + y).prod(), 1.331)


class RegimeTest(unittest.TestCase):
    def test_labels_use_trailing_return(self):
        idx = pd.bdate_range("2026-01-01", periods=6)
        close = pd.Series([100, 100, 110, 104, 100, 90], index=idx, dtype=float)
        label = market_regime(close, window=2, band=0.05)
        self.assertTrue(pd.isna(label.iloc[1]))
        self.assertEqual(label.iloc[2], "yükselen")  # 110/100
        self.assertEqual(label.iloc[3], "yatay")  # 104/100
        self.assertEqual(label.iloc[4], "düşen")  # 100/110
        self.assertEqual(label.iloc[5], "düşen")  # 90/104

    def test_breakdown_uses_previous_label(self):
        idx = pd.bdate_range("2026-01-01", periods=4)
        equity = pd.Series([100, 110, 99, 99], index=idx, dtype=float)
        regime = pd.Series(["yükselen", "düşen", "yatay", "yatay"], index=idx)
        out = regime_breakdown(equity, regime)
        self.assertAlmostEqual(out.loc["yükselen", "total"], 0.10)  # day 2 held under day-1 label
        self.assertAlmostEqual(out.loc["düşen", "total"], -0.10)
        self.assertAlmostEqual(out.loc["yatay", "total"], 0.0)
        self.assertEqual(int(out["days"].sum()), 3)


class ContributionTest(unittest.TestCase):
    def test_sums_per_symbol(self):
        trades = [trade("A", 100, 110), trade("A", 100, 90), trade("B", 10, 30)]
        c = contribution(trades)
        self.assertEqual(list(c.index), ["B", "A"])
        self.assertAlmostEqual(c["B"], 200)
        self.assertAlmostEqual(c["A"], 0)


class VolumeCapTest(unittest.TestCase):
    def test_purchase_capped_by_yesterdays_turnover(self):
        df = frame([10.0] * 40)  # volume 1000 -> turnover 10_000 per day
        cfg = BacktestConfig(max_positions=1, commission=0, slippage=0, max_volume_share=0.01)
        result = run_backtest({"A": df}, always, cfg)
        first = result.trades[0]
        # the 20-day average is complete at the close of index 19, so the first
        # purchase is at index 20, capped at 1% of 10_000
        self.assertEqual(first.entry_date, df.index[20])
        self.assertAlmostEqual(first.shares * first.entry_price, 100.0)

    def test_cap_off_by_default(self):
        df = frame([10.0] * 40)
        result = run_backtest({"A": df}, always, BacktestConfig(max_positions=1, commission=0, slippage=0))
        self.assertAlmostEqual(result.trades[0].shares * result.trades[0].entry_price, 100_000)


class ReportSmokeTest(unittest.TestCase):
    def test_report_on_golden_prices(self):
        frames, bench = load_prices()
        text = reliability_report(
            frames,
            lambda fr: apply_rule(trend_rule(10, 30, 100), fr),
            BacktestConfig(max_positions=5),
            bench,
            start=frames["S01"].index[220],
            name="trend",
        )
        for needle in ("ilk 5 hisse hariç", "2 kat maliyet", "XU100 al-tut", "Yıllara göre", "Piyasa rejimine göre", "beklenti"):
            self.assertIn(needle, text)
        self.assertFalse(math.isnan(len(text)))


if __name__ == "__main__":
    unittest.main()
