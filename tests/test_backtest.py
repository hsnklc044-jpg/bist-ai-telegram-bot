import asyncio
import math
import unittest
from types import SimpleNamespace
from unittest import mock

import pandas as pd

from core.backtest.engine import BacktestConfig, simulate
from core.backtest.signals import score_history
from tests.helpers import FakeProvider, make_ohlcv, offline_market

NO_COSTS = BacktestConfig(commission=0.0, slippage=0.0)


def _frame(rows: list[tuple[float, float, float, float]]) -> pd.DataFrame:
    """Candles from (open, high, low, close) tuples."""

    index = pd.bdate_range("2026-01-05", periods=len(rows))
    df = pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=index)
    df["volume"] = 1_000_000.0
    return df


def _signals(df: pd.DataFrame, scores: list[float], atr: float = 1.0) -> pd.DataFrame:
    return pd.DataFrame({"score": scores, "atr": atr}, index=df.index)


class SignalHistoryTest(unittest.TestCase):
    def test_matches_live_analyzer(self):
        from core.analytics import analyzer

        df = make_ohlcv(rows=400, seed=11)
        history = score_history(df)

        for cut in (60, 120, 250, 400):
            part = df.iloc[:cut]

            with mock.patch.object(analyzer, "load_price_history", return_value=part.copy()):
                live = analyzer.analyze_stock("TEST.IS")

            with self.subTest(cut=cut):
                self.assertEqual(history["score"].iloc[cut - 1], live["score"])
                self.assertEqual(history["signal"].iloc[cut - 1], live["signal"])

    def test_no_score_during_warm_up(self):
        history = score_history(make_ohlcv(rows=100, seed=1))

        self.assertTrue(history["score"].iloc[:59].isna().all())
        self.assertFalse(math.isnan(history["score"].iloc[59]))


class EngineRulesTest(unittest.TestCase):
    def test_entry_is_next_open_never_signal_close(self):
        df = _frame([(10, 10, 10, 10), (11, 12, 11, 11.5), (11.5, 12, 11, 11.8)])
        result = simulate("X", df, NO_COSTS, _signals(df, [80, 50, 50], atr=5))

        trade = result.trades[0]
        self.assertEqual(trade.entry_date, df.index[1])
        self.assertEqual(trade.entry_price, 11)
        self.assertEqual(trade.reason, "end")
        self.assertEqual(trade.exit_price, 11.8)

    def test_stop_wins_when_candle_touches_both(self):
        df = _frame([(10, 10, 10, 10), (10, 20, 1, 10)])
        trade = simulate("X", df, NO_COSTS, _signals(df, [80, 50])).trades[0]

        self.assertEqual(trade.reason, "stop")
        self.assertEqual(trade.exit_price, 8)

    def test_gap_through_stop_fills_at_open(self):
        df = _frame([(10, 10, 10, 10), (10, 10.5, 9.5, 10), (6, 7, 5, 6.5)])
        trade = simulate("X", df, NO_COSTS, _signals(df, [80, 50, 50])).trades[0]

        self.assertEqual(trade.reason, "stop")
        self.assertEqual(trade.exit_price, 6)

    def test_target_and_sell_signal(self):
        df = _frame([(10, 10, 10, 10), (10, 15, 9.5, 14), (14, 14, 14, 14)])
        trade = simulate("X", df, NO_COSTS, _signals(df, [80, 50, 50])).trades[0]
        self.assertEqual((trade.reason, trade.exit_price), ("target", 14))

        df = _frame([(10, 10, 10, 10), (10, 10.5, 9.5, 10), (9.8, 10, 9.5, 9.9)])
        trade = simulate("X", df, NO_COSTS, _signals(df, [80, 30, 50])).trades[0]
        self.assertEqual((trade.reason, trade.exit_date), ("signal", df.index[2]))
        self.assertEqual(trade.exit_price, 9.8)

    def test_holding_limit(self):
        flat = [(10, 10.1, 9.9, 10)] * 8
        df = _frame(flat)
        config = BacktestConfig(commission=0.0, slippage=0.0, max_hold_days=3)
        trade = simulate("X", df, config, _signals(df, [80] + [50] * 7)).trades[0]

        self.assertEqual(trade.reason, "time")
        self.assertEqual(trade.days, 3)
        self.assertEqual(trade.exit_date, df.index[4])

    def test_costs_are_charged_on_both_sides(self):
        df = _frame([(10, 10, 10, 10)] * 3)
        config = BacktestConfig(commission=0.01, slippage=0.0)
        result = simulate("X", df, config, _signals(df, [80, 50, 50]))

        self.assertAlmostEqual(result.equity.iloc[-1], 0.99 * 0.99)
        self.assertAlmostEqual(result.metrics.avg_trade, 0.99 * 0.99 - 1)

    def test_future_candles_do_not_change_the_past(self):
        df = make_ohlcv(rows=700, seed=5)
        full = simulate("X", df)
        part = simulate("X", df.iloc[:500])

        cutoff = df.index[498]
        closed_full = [t for t in full.trades if t.exit_date <= cutoff]
        closed_part = [t for t in part.trades if t.exit_date <= cutoff]

        self.assertGreater(len(closed_part), 0)
        self.assertEqual(
            [(t.entry_date, t.exit_date, t.reason) for t in closed_full],
            [(t.entry_date, t.exit_date, t.reason) for t in closed_part],
        )
        pd.testing.assert_series_equal(full.equity.iloc[:499], part.equity.iloc[:499])


class ExitVariantsTest(unittest.TestCase):
    def test_trailing_stop_follows_highest_close(self):
        df = _frame(
            [(10, 10, 10, 10), (10, 12, 10, 12), (12, 14, 12, 14), (14, 14, 12.5, 13)]
        )
        config = BacktestConfig(commission=0.0, slippage=0.0, target_atr=None, trailing_atr=1.0)
        trade = simulate("X", df, config, _signals(df, [80, 50, 50, 50])).trades[0]

        # highest close 14 after day 2 -> stop 13, hit on day 3 (low 12.5)
        self.assertEqual((trade.reason, trade.exit_price), ("stop", 13))

    def test_no_target_lets_winners_run(self):
        df = _frame([(10, 10, 10, 10), (10, 30, 10, 30), (30, 30, 30, 30)])
        config = BacktestConfig(commission=0.0, slippage=0.0, target_atr=None)
        trade = simulate("X", df, config, _signals(df, [80, 50, 50])).trades[0]

        self.assertEqual((trade.reason, trade.exit_price), ("end", 30))

    def test_uptrend_ignores_sell_signal(self):
        df = _frame([(10, 10, 10, 10), (10, 10.5, 9.5, 10), (10, 10.5, 9.5, 10)])
        signals = _signals(df, [80, 30, 50])
        config = BacktestConfig(commission=0.0, slippage=0.0, hold_in_uptrend=True)

        held = simulate("X", df, config, signals, pd.Series(True, index=df.index))
        sold = simulate("X", df, config, signals, pd.Series(False, index=df.index))

        self.assertEqual(held.trades[0].reason, "end")
        self.assertEqual(sold.trades[0].reason, "signal")

    def test_idle_cash_earns_interest(self):
        df = _frame([(10, 10, 10, 10)] * 253)
        config = BacktestConfig(cash_rate=0.5)
        result = simulate("X", df, config, _signals(df, [50] * 253))

        self.assertAlmostEqual(result.equity.iloc[-1], 1.5)
        self.assertEqual(result.trades, [])


class JumpDetectionTest(unittest.TestCase):
    def test_limit_compounds_over_market_closures(self):
        from core.market.quality import suspicious_jumps

        index = pd.to_datetime(["2023-02-06", "2023-02-07", "2023-02-15", "2024-09-06",
                                "2024-09-09"])
        df = pd.DataFrame({"close": [100, 100, 122, 120, 42]}, index=index)

        jumps = suspicious_jumps(df)

        self.assertEqual(list(jumps.index), [pd.Timestamp("2024-09-09")])

    def test_universe_leaves_out_unadjusted_stock(self):
        from core.backtest.runner import load_dataset

        fake = FakeProvider()
        broken = make_ohlcv(rows=600, seed=8)
        broken.iloc[400:, :4] *= 0.35
        fake.overrides["HEKTS.IS"] = broken

        with offline_market(fake):
            data = load_dataset(["THYAO.IS", "HEKTS.IS"])

        self.assertEqual(list(data.prices), ["THYAO.IS"])
        self.assertIn("sıçrama", data.skipped["HEKTS.IS"])

    def test_compare_uses_same_data_for_every_variant(self):
        from core.backtest.runner import (
            ROTATIONS,
            VARIANTS,
            compare,
            format_comparison,
            load_dataset,
        )

        with offline_market():
            data = load_dataset(["THYAO.IS", "EREGL.IS", "GARAN.IS"])
            lines = compare(data)

        names = [line.name for line in lines]
        self.assertEqual(
            names, [*VARIANTS, *ROTATIONS, "Aynı hisseler al-tut", "XU100 al-tut"]
        )
        self.assertEqual(len({line.equity.index[0] for line in lines}), 1)
        self.assertTrue(all(line.equity.iloc[0] == 1.0 for line in lines))
        self.assertIn("XU100 al-tut", format_comparison(lines, data))


class RunnerTest(unittest.TestCase):
    def test_universe_report(self):
        from core.backtest.runner import format_portfolio, format_symbol, run_universe

        fake = FakeProvider()
        fake.overrides["EMPTY.IS"] = make_ohlcv(rows=600).iloc[0:0]

        with offline_market(fake):
            result = run_universe(["THYAO.IS", "EREGL.IS", "EMPTY.IS"])

        self.assertEqual([r.symbol for r in result.results], ["THYAO.IS", "EREGL.IS"])
        self.assertEqual(result.skipped, {"EMPTY.IS": "veri yok"})
        self.assertIsNotNone(result.benchmark_return)
        self.assertAlmostEqual(result.equity.iloc[0], 1.0)

        text = format_portfolio(result)
        self.assertIn("QUANTBIST BACKTEST", text)
        self.assertIn("THYAO", text)
        self.assertIn("EMPTY.IS", text)
        self.assertIn("THYAO.IS", format_symbol(result.results[0]))

    def test_bot_command_without_data(self):
        from bot.backtest import NO_DATA, backtest

        sent: list[str] = []

        async def reply_text(text, **kwargs):
            sent.append(text)

        message = SimpleNamespace(reply_text=reply_text)
        update = SimpleNamespace(message=message, effective_message=message)

        with offline_market(FakeProvider(fail=True)):
            asyncio.run(backtest(update, SimpleNamespace(args=[])))
            asyncio.run(backtest(update, SimpleNamespace(args=["THYAO"])))

        self.assertEqual(sent.count(NO_DATA), 2)

    def test_bot_command_single_symbol(self):
        from bot.backtest import backtest

        sent: list[str] = []

        async def reply_text(text, **kwargs):
            sent.append(text)

        message = SimpleNamespace(reply_text=reply_text)
        update = SimpleNamespace(message=message, effective_message=message)

        with offline_market():
            asyncio.run(backtest(update, SimpleNamespace(args=["thyao"])))

        self.assertIn("BACKTEST THYAO.IS", sent[-1])


if __name__ == "__main__":
    unittest.main()
