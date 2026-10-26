import unittest

import pandas as pd

from core.backtest.engine import BacktestConfig, buy_and_hold, compute_metrics, run_backtest


def frame(closes, opens=None, lows=None, start="2026-01-05"):
    idx = pd.bdate_range(start=start, periods=len(closes))
    closes = pd.Series(closes, index=idx, dtype=float)
    opens = pd.Series(opens if opens is not None else closes.values, index=idx, dtype=float)
    # a small intraday range so that no bar looks like a locked limit day
    lows = pd.Series(
        lows if lows is not None else (closes.combine(opens, min) * 0.999).values, index=idx
    )
    return pd.DataFrame(
        {
            "open": opens,
            "high": closes.combine(opens, max) * 1.001,
            "low": lows,
            "close": closes,
            "volume": 1000.0,
        }
    )


def always(df):
    return pd.DataFrame({"enter": True, "exit": False, "rank": 1.0}, index=df.index)


def enter_on(day_index):
    def rule(df):
        enter = pd.Series(False, index=df.index)
        enter.iloc[day_index] = True
        return pd.DataFrame({"enter": enter, "exit": False, "rank": 1.0}, index=df.index)

    return rule


NO_COST = BacktestConfig(max_positions=1, commission=0, slippage=0)


class EngineTest(unittest.TestCase):
    def test_entry_at_next_open_not_signal_close(self):
        df = frame([10, 10, 20, 20], opens=[10, 10, 15, 20])
        result = run_backtest({"A": df}, enter_on(1), NO_COST)

        trade = result.trades[0]
        self.assertEqual(trade.entry_date, df.index[2])
        self.assertEqual(trade.entry_price, 15)

    def test_equity_follows_price_without_costs(self):
        df = frame([10, 11, 12, 13])
        result = run_backtest({"A": df}, always, NO_COST)

        # enters at day-1 open (11), ends at 13
        self.assertAlmostEqual(result.equity.iloc[-1], 100_000 * 13 / 11)

    def test_costs_reduce_returns(self):
        df = frame([10, 11, 12, 13])
        cheap = run_backtest({"A": df}, always, NO_COST).equity.iloc[-1]
        costly = run_backtest(
            {"A": df}, always, BacktestConfig(max_positions=1, commission=0.01, slippage=0)
        ).equity.iloc[-1]

        # open position is marked at the close; the exit cost is paid in the final trade
        self.assertAlmostEqual(costly, 100_000 * 13 / (11 * 1.01))
        self.assertLess(costly, cheap)

        trade = run_backtest(
            {"A": df}, always, BacktestConfig(max_positions=1, commission=0.01, slippage=0)
        ).trades[0]
        self.assertAlmostEqual(trade.exit_price, 13 * 0.99)

    def test_gap_below_stop_fills_at_open(self):
        closes = [10] * 20 + [10, 10, 6]
        opens = [10] * 20 + [10, 10, 6]
        lows = [9.9] * 20 + [9.9, 9.9, 5.5]
        df = frame(closes, opens=opens, lows=lows)
        result = run_backtest(
            {"A": df}, enter_on(19), BacktestConfig(max_positions=1, commission=0, slippage=0, atr_stop=2)
        )

        trade = result.trades[0]
        self.assertEqual(trade.exit_reason, "stop")
        self.assertEqual(trade.exit_price, 6)

    def test_slots_limit_positions(self):
        frames = {s: frame([10, 11, 12, 13, 14]) for s in "ABCDEFG"}
        result = run_backtest(frames, always, BacktestConfig(max_positions=3, commission=0, slippage=0))

        self.assertEqual(len(result.trades), 3)
        self.assertAlmostEqual(result.exposure.iloc[-1], 1.0)

    def test_exit_signal_sells_next_open(self):
        df = frame([10, 10, 12, 12, 9], opens=[10, 10, 11, 13, 9])

        def rule(d):
            exit_ = pd.Series(False, index=d.index)
            exit_.iloc[2] = True
            return pd.DataFrame({"enter": True, "exit": exit_, "rank": 1.0}, index=d.index)

        result = run_backtest({"A": df}, rule, NO_COST)
        first = result.trades[0]

        self.assertEqual(first.exit_date, df.index[3])
        self.assertEqual(first.exit_price, 13)
        self.assertEqual(first.exit_reason, "signal")


class LimitLockTest(unittest.TestCase):
    def locked_down_frame(self):
        # day 3 and 4 are locked at the lower limit (high == low, -10%)
        closes = [10, 10, 10, 9, 8.1, 8.0, 8.2]
        opens = [10, 10, 10, 9, 8.1, 8.1, 8.1]
        df = frame(closes, opens=opens)
        df["high"] = df[["open", "close"]].max(axis=1)
        df["low"] = df[["open", "close"]].min(axis=1)
        df.loc[df.index[5], "high"] = 8.3
        return df

    def test_cannot_sell_into_locked_limit_down(self):
        df = self.locked_down_frame()

        def rule(d):
            exit_ = pd.Series(False, index=d.index)
            exit_.iloc[2] = True  # sell at day-3 open, which is locked
            return pd.DataFrame({"enter": True, "exit": exit_, "rank": 1.0}, index=d.index)

        trade = run_backtest({"A": df}, rule, NO_COST).trades[0]

        self.assertEqual(trade.exit_date, df.index[5])
        self.assertEqual(trade.exit_price, 8.1)

    def test_lock_can_be_switched_off(self):
        df = self.locked_down_frame()

        def rule(d):
            exit_ = pd.Series(False, index=d.index)
            exit_.iloc[2] = True
            return pd.DataFrame({"enter": True, "exit": exit_, "rank": 1.0}, index=d.index)

        cfg = BacktestConfig(max_positions=1, commission=0, slippage=0, respect_limit_locks=False)
        trade = run_backtest({"A": df}, rule, cfg).trades[0]

        self.assertEqual(trade.exit_date, df.index[3])

    def test_cannot_buy_locked_limit_up(self):
        closes = [10, 10, 11, 11.5]
        df = frame(closes, opens=[10, 10, 11, 11])
        df["high"] = df[["open", "close"]].max(axis=1)
        df["low"] = df[["open", "close"]].min(axis=1)  # day 2 locked +10%

        trade = run_backtest({"A": df}, enter_on(1), NO_COST).trades

        self.assertEqual(trade, [])


class MetricsTest(unittest.TestCase):
    def test_drawdown_and_return(self):
        idx = pd.bdate_range("2025-01-01", periods=4)
        m = compute_metrics(pd.Series([100, 120, 90, 110], index=idx, dtype=float))

        self.assertAlmostEqual(m["total_return"], 0.10)
        self.assertAlmostEqual(m["max_drawdown"], -0.25)

    def test_buy_and_hold_equal_weight(self):
        frames = {"A": frame([10, 20]), "B": frame([10, 10])}

        self.assertAlmostEqual(buy_and_hold(frames).iloc[-1], 150_000)


class ReportSmokeTest(unittest.TestCase):
    def test_report_runs_on_offline_market(self):
        from core.backtest.run import run_report
        from core.market import store
        from core.market.universe import BENCHMARK, load_universe
        from tests.helpers import offline_market

        with offline_market():
            store.update([BENCHMARK, *load_universe()])
            text = run_report(positions=3, start="2025-01-01")

        self.assertIn("Bot sinyali", text)
        self.assertIn("XU100 al-tut", text)
        self.assertIn("Yıllık getiriler", text)


class ResearchSmokeTest(unittest.TestCase):
    def test_research_report_runs(self):
        from unittest import mock

        import pandas as pd

        from core.backtest import research
        from core.market import store
        from core.market.universe import BENCHMARK
        from tests.helpers import offline_market

        symbols = [f"R{i}.IS" for i in range(8)]

        def panel(index, names, **_):
            return pd.DataFrame(True, index=index, columns=names)

        texts = {}
        with offline_market(), mock.patch("core.backtest.run.load_universe", return_value=symbols), \
                mock.patch("core.market.membership.ever_members", return_value=symbols), \
                mock.patch("core.market.membership.membership_panel", side_effect=panel), \
                mock.patch.object(research, "GRID", [dict(lookback=63, top_n=3, regime=False)]):
            store.update([BENCHMARK, *symbols])
            records = []
            for universe in ("pit", "today"):
                texts[universe] = research.research_report(
                    start="2025-06-01", positions=3, universe=universe, records=records
                )

        # 6 strategies + XU100 (pit); + equal weight (today)
        self.assertEqual(len(records), 15)
        self.assertEqual({r["universe"] for r in records}, {"pit", "today"})
        self.assertTrue(all(r["verdict"] for r in records if r["strategy"].startswith("Momentum")))
        self.assertEqual([r["verdict"] for r in records if r["strategy"] == "XU100 al-tut"], ["", ""])

        for text in texts.values():
            self.assertIn("walk-forward", text)
            self.assertIn("XU100 al-tut", text)
            self.assertIn("Bonferroni", text)
            self.assertIn("XU100'ü geçen pencere", text)
        self.assertIn("geçmiş BIST 100 üyeliği", texts["pit"])
        self.assertNotIn("Eşit ağırlık", texts["pit"])
        self.assertIn("BUGÜNKÜ liste", texts["today"])
        self.assertIn("Eşit ağırlık", texts["today"])
