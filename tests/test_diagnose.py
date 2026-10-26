import unittest

import pandas as pd

from core.backtest.diagnose import deepest_drawdown, diagnose
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
