import unittest

import pandas as pd

from core.backtest.diagnose import deepest_drawdown, diagnose, impossible_moves
from core.backtest.engine import BacktestConfig, BacktestResult, Trade, run_backtest
from core.strategy.rules import momentum_signals
from tests.helpers import make_ohlcv


class DrawdownTest(unittest.TestCase):
    def test_peak_and_trough(self):
        index = pd.bdate_range("2026-01-05", periods=6)
        equity = pd.Series([100, 120, 90, 60, 80, 130], index=index, dtype=float)

        dd = deepest_drawdown(equity)

        self.assertEqual((dd.peak, dd.trough), (index[1], index[3]))
        self.assertAlmostEqual(dd.depth, -0.5)


class ImpossibleMoveTest(unittest.TestCase):
    def test_limit_compounds_over_gaps_and_ignores_market_wide_days(self):
        index = pd.to_datetime(
            ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-11", "2024-01-12", "2024-01-15"]
        )
        df = pd.DataFrame({"close": [100, 109, 95, 120, 60, 50]}, index=index)

        moves = impossible_moves(df, market_wide=set())
        self.assertEqual(list(moves.index), [pd.Timestamp("2024-01-04"), index[4], index[5]])

        limit_day = pd.DataFrame({"close": [100.0, 110.4, 99.0]}, index=index[:3])
        self.assertTrue(impossible_moves(limit_day, set()).empty)  # tick-rounded limit moves

        moves = impossible_moves(df, market_wide={index[4]})
        self.assertNotIn(index[4], moves.index)
        self.assertNotIn(index[3], moves.index)  # +26% over 5 sessions is allowed


class DiagnoseTest(unittest.TestCase):
    def test_report_flags_bad_data_in_worst_trades(self):
        frames = {f"S{i}.IS": make_ohlcv(rows=300, seed=i, vol=0.01) for i in range(3)}
        broken = frames["S0.IS"].copy()
        broken.iloc[200:, :4] *= 0.4
        frames["S0.IS"] = broken
        day = broken.index[200]

        trade = Trade(
            symbol="S0.IS",
            entry_date=broken.index[150],
            entry_price=float(broken["open"].iloc[150]),
            exit_date=broken.index[250],
            exit_price=float(broken["close"].iloc[250]),
            shares=100.0,
        )
        equity = 100_000 + 100 * (broken["close"] - broken["close"].iloc[150])
        result = BacktestResult(
            equity=equity.iloc[150:251],
            trades=[trade],
            exposure=pd.Series(dtype=float),
            config=BacktestConfig(),
        )

        text = diagnose(result, frames)

        self.assertIn("En derin düşüş", text)
        self.assertIn(f"{broken.index[250].date()}", text)
        self.assertIn(f"⚠ {day.date()} -6", text)
        self.assertIn("kayba katkı", text)
        self.assertIn("veri hatası içeriyor olabilir", text)

    def test_runs_on_a_real_backtest(self):
        frames = {f"S{i}.IS": make_ohlcv(rows=400, seed=i) for i in range(5)}
        signals = momentum_signals(frames, 126, top_n=2)
        result = run_backtest(frames, signals, BacktestConfig(max_positions=2))

        text = diagnose(result, frames)

        self.assertIn("En kötü", text)
        self.assertNotIn("<10", text)


if __name__ == "__main__":
    unittest.main()
