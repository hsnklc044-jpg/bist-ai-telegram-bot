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

    def test_ranks_only_eligible_stocks(self):
        frames = universe()
        index = frames["S0"].index
        eligible = pd.DataFrame(True, index=index, columns=list(frames))
        eligible["S7"] = False  # strongest, but not an index member
        eligible.loc[index[300]:, "S6"] = False  # leaves the index

        result = run_backtest(
            frames, momentum_signals(frames, lookback=126, top_n=3, eligible=eligible), BacktestConfig(max_positions=3)
        )

        held = {t.symbol for t in result.trades}
        self.assertNotIn("S7", held)
        self.assertTrue(held <= {"S3", "S4", "S5", "S6"}, held)  # S3 replaces S6 once it leaves
        late = [t for t in result.trades if t.symbol == "S6" and t.entry_date > index[302]]
        self.assertEqual(late, [])

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


class LowVolatilityTest(unittest.TestCase):
    """Aşama 3 H1 (RESEARCH_LOG): on each month's last session, the top_n members with the lowest 60-session volatility."""

    def frames(self):
        import numpy as np
        import pandas as pd

        index = pd.bdate_range("2026-01-01", "2026-04-30")
        rng = np.random.default_rng(3)
        out = {}
        for i, sigma in enumerate((0.005, 0.01, 0.02, 0.04)):  # S0 calmest … S3 wildest
            close = 100 * np.exp(np.cumsum(rng.normal(0, sigma, len(index))))
            out[f"S{i}.IS"] = pd.DataFrame({"open": close, "high": close, "low": close, "close": close,
                                            "volume": 1e6}, index=index)
        return out

    def test_calmest_two_are_held_from_the_month_end(self):
        import pandas as pd

        from core.strategy.rules import low_volatility_signals

        sig = low_volatility_signals(self.frames(), window=60, top_n=2)
        march_end = pd.Timestamp("2026-03-31")  # first month end with 60 returns
        for s in ("S0.IS", "S1.IS"):
            self.assertTrue(sig[s].at[march_end, "enter"], s)
            self.assertFalse(sig[s].loc[:march_end - pd.Timedelta(days=1), "enter"].any(), s)  # no history before
        for s in ("S2.IS", "S3.IS"):
            self.assertFalse(sig[s]["enter"].any(), s)
            self.assertTrue(sig[s].at[march_end, "exit"], s)
        self.assertGreater(sig["S0.IS"].at[march_end, "rank"], sig["S1.IS"].at[march_end, "rank"])

    def test_only_members_that_day_are_ranked(self):
        import pandas as pd

        from core.strategy.rules import low_volatility_signals

        frames = self.frames()
        index = frames["S0.IS"].index
        eligible = pd.DataFrame(True, index=index, columns=list(frames))
        eligible["S0.IS"] = False  # the calmest is not a member
        sig = low_volatility_signals(frames, window=60, top_n=2, eligible=eligible)
        march_end = pd.Timestamp("2026-03-31")
        self.assertFalse(sig["S0.IS"]["enter"].any())
        self.assertTrue(sig["S1.IS"].at[march_end, "enter"])
        self.assertTrue(sig["S2.IS"].at[march_end, "enter"])



def _index_frame(closes, start):
    import pandas as pd

    index = pd.bdate_range(start, periods=len(closes))
    return pd.DataFrame({"open": closes, "high": closes, "low": closes, "close": closes, "volume": 1e9}, index=index)


class IndexTrendTest(unittest.TestCase):
    """Aşama 3 H2: at each month's last session, hold XU100 for the next month if it closes above its 200-session mean."""

    def test_decided_on_the_last_session_of_the_month(self):
        import pandas as pd

        from core.strategy.rules import index_trend_signals

        closes = [100.0] * 200 + [110.0] * 40  # above the mean from the 201st session (2025-10-08)
        df = _index_frame(closes, "2025-01-01")
        sig = index_trend_signals(df, window=200)
        month_end = pd.Timestamp("2025-10-31")
        self.assertFalse(sig.loc[:month_end - pd.Timedelta(days=1), "enter"].any())  # above the mean mid-month: wait
        self.assertTrue(sig.loc[month_end:, "enter"].all())
        self.assertTrue(sig.at[pd.Timestamp("2025-10-08"), "exit"])

    def test_below_the_mean_is_cash(self):
        from core.strategy.rules import index_trend_signals

        closes = [100.0] * 200 + [90.0] * 40
        sig = index_trend_signals(_index_frame(closes, "2025-01-01"), window=200)
        self.assertFalse(sig["enter"].any())
        self.assertTrue(sig["exit"].all())


class TurnOfMonthTest(unittest.TestCase):
    """Aşama 3 H3: hold XU100 over each month's last 3 and next month's first 3 sessions (orders fill next open)."""

    def test_signal_days_by_hand(self):
        import pandas as pd

        from core.strategy.rules import turn_of_month_signals

        df = _index_frame([100.0] * 45, "2025-09-01")  # 1 Sep – 31 Oct 2025; past sessions are the candles
        sig = turn_of_month_signals(df, sessions=3)
        held_at_close = set(sig.index[sig["enter"]].strftime("%m-%d"))
        # September starts 1, 2, 3: held at the closes of 1 and 2.
        # September ends 26, 29, 30: the signal comes at the close of 25 -> bought at the open of 26.
        # October starts 1, 2, 3: still held at the close of 2 -> sold at the open of 6 (4th session).
        # October ends 29, 30, 31: bought at the open of 29; held into November.
        self.assertEqual(held_at_close, {"09-01", "09-02", "09-25", "09-26", "09-29", "09-30", "10-01", "10-02",
                                         "10-28", "10-29", "10-30", "10-31"})
        self.assertTrue(sig.at[pd.Timestamp("2025-10-03"), "exit"])

    def test_future_sessions_come_from_the_holiday_calendar(self):
        import pandas as pd

        from core.strategy.rules import turn_of_month_signals

        # October 2026: 29th is a full holiday, so the last sessions are 27, 28 (half day), 30.
        index = pd.bdate_range("2026-10-01", "2026-10-27")  # the data ends before the window
        df = pd.DataFrame({"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1.0}, index=index)
        sig = turn_of_month_signals(df, sessions=3)
        self.assertTrue(sig.at[pd.Timestamp("2026-10-26"), "enter"])  # next session 27 = 3rd from last
        self.assertFalse(sig.at[pd.Timestamp("2026-10-23"), "enter"])
