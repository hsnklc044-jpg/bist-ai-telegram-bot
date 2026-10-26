import unittest

import pandas as pd

from core.backtest.engine import BacktestConfig, run_backtest
from core.backtest.walkforward import walk_forward
from core.strategy.rules import momentum_signals, regime_filter, with_regime
from tests.helpers import make_ohlcv


def universe(n=8, rows=400):
    # symbol i drifts by i * 0.3% a day: higher index = stronger momentum
    return {f"S{i}": make_ohlcv(rows=rows, seed=i, drift=0.003 * i, vol=0.003) for i in range(n)}


class MomentumTest(unittest.TestCase):
    def test_holds_the_strongest_stocks(self):
        frames = universe()
        result = run_backtest(
            frames, momentum_signals(frames, lookback=126, top_n=3), BacktestConfig(max_positions=3)
        )

        held = {t.symbol for t in result.trades}
        self.assertTrue(held <= {"S5", "S6", "S7"}, held)

    def test_rebalances_only_at_month_end(self):
        frames = universe()
        sig = momentum_signals(frames, lookback=63, top_n=3)["S7"]
        changes = sig["enter"].astype(int).diff().fillna(0) != 0
        changed_days = sig.index[changes]

        month_ends = sig.index.to_series().groupby(sig.index.to_period("M")).max()
        self.assertTrue(set(changed_days) <= set(month_ends))

    def test_bad_regime_means_cash(self):
        frames = universe()
        regime = pd.Series(False, index=frames["S0"].index)
        result = run_backtest(
            frames, momentum_signals(frames, top_n=3, regime=regime), BacktestConfig(max_positions=3)
        )

        self.assertEqual(result.trades, [])

    def test_regime_filter_uses_long_average(self):
        bench = make_ohlcv(rows=300, drift=0.01, vol=0.001)
        regime = regime_filter(bench)

        self.assertFalse(regime.iloc[:199].any())
        self.assertTrue(regime.iloc[-1])

    def test_with_regime_forces_exit(self):
        idx = pd.bdate_range("2026-01-01", periods=4)
        sig = {"A": pd.DataFrame({"enter": True, "exit": False, "rank": 1.0}, index=idx)}
        regime = pd.Series([True, True, False, False], index=idx)

        out = with_regime(sig, regime)["A"]

        self.assertEqual(list(out["enter"]), [True, True, False, False])
        self.assertEqual(list(out["exit"]), [False, False, True, True])


class WalkForwardTest(unittest.TestCase):
    def test_only_out_of_sample_windows_reported(self):
        frames = universe(rows=700)
        start = frames["S0"].index[400]
        grid = [dict(lookback=63, top_n=2), dict(lookback=126, top_n=3)]

        wf = walk_forward(
            frames,
            lambda p: momentum_signals(frames, lookback=p["lookback"], top_n=p["top_n"]),
            grid,
            BacktestConfig(),
            start=start.date().isoformat(),
            train_months=12,
            test_months=3,
        )

        self.assertGreaterEqual(wf.equity.index[0], start)
        self.assertTrue(all(s.params in grid for s in wf.steps))
        self.assertTrue(all(s.train_start < s.test_start for s in wf.steps))
        self.assertGreater(wf.metrics["trades"], 0)
