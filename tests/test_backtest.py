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


class RunnerTest(unittest.TestCase):
    def test_universe_report(self):
        from core.backtest.runner import format_portfolio, format_symbol, run_universe

        fake = FakeProvider()
        fake.overrides["EMPTY.IS"] = make_ohlcv(rows=600).iloc[0:0]

        with offline_market(fake):
            result = run_universe(["THYAO.IS", "EREGL.IS", "EMPTY.IS"])

        self.assertEqual([r.symbol for r in result.results], ["THYAO.IS", "EREGL.IS"])
        self.assertEqual(result.skipped, ["EMPTY.IS"])
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
