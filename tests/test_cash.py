import tempfile
import unittest
from pathlib import Path

import pandas as pd

from core.backtest.cash import (
    FixedRate,
    FundPrices,
    RateSeries,
    load_rate_series,
    parse_cash_option,
)
from core.backtest.engine import BacktestConfig, run_backtest
from core.strategy.rules import trend_rule
from tests.golden import load_prices
from tests.test_backtest import frame

T = pd.Timestamp


def never(df):
    return pd.DataFrame({"enter": False, "exit": False, "rank": 0.0}, index=df.index)


class ConventionTest(unittest.TestCase):
    def test_simple_rate_compounds_daily_over_calendar_days(self):
        g = FixedRate(0.45).growth(T("2025-01-01"), T("2026-01-01"))
        self.assertAlmostEqual(g.factor - 1, (1 + 0.45 / 365) ** 365 - 1, places=12)
        self.assertAlmostEqual(g.factor - 1, 0.5679, places=4)

    def test_weekend_earns_three_days(self):
        friday, monday = T("2026-10-16"), T("2026-10-19")
        g = FixedRate(0.365).growth(friday, monday)
        self.assertAlmostEqual(g.factor, 1.001**3, places=12)

    def test_engine_idle_cash_over_one_year(self):
        df = frame([10.0] * 262, start="2025-01-01")  # business days for ~one year
        config = BacktestConfig(cash=FixedRate(0.45), commission=0, slippage=0)
        result = run_backtest({"A": df}, never, config)
        days = (df.index[-1] - df.index[0]).days
        self.assertAlmostEqual(result.equity.iloc[-1], 100_000 * (1 + 0.45 / 365) ** days, places=4)
        self.assertAlmostEqual(result.metrics["cash_interest"], result.equity.iloc[-1] - 100_000)
        self.assertEqual(result.metrics["cash_missing_days"], 0)
        # dividing by 365 but accruing only on trading days would lose about a third
        wrong = (1 + 0.45 / 365) ** (len(df) - 1) - 1
        self.assertLess(wrong, 0.75 * (result.equity.iloc[-1] / 100_000 - 1))

    def test_default_is_no_interest(self):
        df = frame([10.0] * 30)
        result = run_backtest({"A": df}, never, BacktestConfig())
        self.assertEqual(result.equity.iloc[-1], 100_000)
        self.assertNotIn("cash_interest", result.metrics)


class RateSeriesTest(unittest.TestCase):
    def test_rate_applies_from_its_effective_date(self):
        # decision announced Thursday 2026-03-12 -> applies from Friday 2026-03-13
        rates = pd.Series({T("2026-01-01"): 0.365, T("2026-03-13"): 0.73})
        model = RateSeries(rates)
        before = model.growth(T("2026-03-11"), T("2026-03-12")).factor
        after = model.growth(T("2026-03-12"), T("2026-03-13")).factor
        self.assertAlmostEqual(before, 1.001, places=12)
        self.assertAlmostEqual(after, 1.002, places=12)

    def test_future_rows_do_not_change_the_past(self):
        rates = pd.Series({T("2026-01-01"): 0.365})
        later = pd.concat([rates, pd.Series({T("2026-06-01"): 2.0})])
        a = RateSeries(rates).growth(T("2026-03-01"), T("2026-05-31")).factor
        b = RateSeries(later).growth(T("2026-03-01"), T("2026-05-31")).factor
        self.assertEqual(a, b)

    def test_withholding_and_spread(self):
        rates = pd.Series({T("2026-01-01"): 0.50})
        tax = pd.Series({T("2026-01-01"): 0.10, T("2026-02-01"): 0.20})
        model = RateSeries(rates, tax, spread=0.05)
        jan = model.growth(T("2026-01-10"), T("2026-01-11")).factor
        feb = model.growth(T("2026-02-10"), T("2026-02-11")).factor
        self.assertAlmostEqual(jan, 1 + 0.45 * 0.9 / 365, places=12)
        self.assertAlmostEqual(feb, 1 + 0.45 * 0.8 / 365, places=12)

    def test_missing_period_is_not_filled(self):
        rates = pd.Series({T("2026-01-05"): 0.365})
        g = RateSeries(rates).growth(T("2026-01-01"), T("2026-01-07"))
        self.assertEqual(g.missing_days, 3)  # interest days are Jan 2..7; no rate for Jan 2, 3, 4
        self.assertAlmostEqual(g.factor, 1.001**3, places=12)  # Jan 5, 6, 7


class FundPricesTest(unittest.TestCase):
    prices = pd.Series({T("2026-01-02"): 1.00, T("2026-01-05"): 1.003, T("2026-01-06"): 1.004})

    def test_factor_is_price_ratio(self):
        g = FundPrices(self.prices).growth(T("2026-01-02"), T("2026-01-05"))
        self.assertAlmostEqual(g.factor, 1.003, places=12)

    def test_tax_on_gain(self):
        g = FundPrices(self.prices, withholding=0.10).growth(T("2026-01-02"), T("2026-01-05"))
        self.assertAlmostEqual(g.factor, 1 + 0.003 * 0.9, places=12)

    def test_outside_known_prices_earns_nothing(self):
        g = FundPrices(self.prices).growth(T("2026-01-06"), T("2026-01-08"))
        self.assertEqual(g.factor, 1.0)
        self.assertEqual(g.missing_days, 2)


class SettlementTest(unittest.TestCase):
    def test_sale_proceeds_earn_after_t_plus_2(self):
        closes = [10.0] * 20
        df = frame(closes, start="2026-01-05")

        def one_trade(d):
            enter = pd.Series(False, index=d.index)
            leave = pd.Series(False, index=d.index)
            enter.iloc[0] = True
            leave.iloc[4] = True  # sold at the open of index 5
            return pd.DataFrame({"enter": enter, "exit": leave, "rank": 1.0}, index=d.index)

        rate = 0.365  # 0.1% per calendar day
        cfg = dict(max_positions=1, commission=0, slippage=0, cash=FixedRate(rate))
        t2 = run_backtest({"A": df}, one_trade, BacktestConfig(**cfg, settlement_days=2))
        t0 = run_backtest({"A": df}, one_trade, BacktestConfig(**cfg, settlement_days=0))

        sold = df.index[5]
        settled = df.index[7]
        lost_days = (settled - sold).days
        expected_gap = 100_000 * ((1.001**lost_days) - 1)
        gap = t0.equity.iloc[-1] - t2.equity.iloc[-1]
        # the T+2 run misses interest for the settlement days (compounded later)
        self.assertGreater(gap, 0.99 * expected_gap)
        self.assertLess(gap, 1.05 * expected_gap)


class NoEffectOnDecisionsTest(unittest.TestCase):
    def test_trades_happen_on_the_same_days(self):
        frames, _ = load_prices()
        start = frames["S01"].index[220]
        base = run_backtest(frames, trend_rule(10, 30, 100), BacktestConfig(), start=start)
        paid = run_backtest(
            frames, trend_rule(10, 30, 100), BacktestConfig(cash=FixedRate(0.40)), start=start
        )

        def days(r):
            return [(t.symbol, t.entry_date, t.exit_date, t.exit_reason) for t in r.trades]

        self.assertEqual(days(base), days(paid))
        self.assertGreater(paid.equity.iloc[-1], base.equity.iloc[-1])


class LoaderTest(unittest.TestCase):
    def write(self, text):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8")
        tmp.write(text)
        tmp.close()
        self.addCleanup(Path(tmp.name).unlink)
        return tmp.name

    def test_rows_need_a_source(self):
        path = self.write("effective_date,rate,source\n2026-01-01,0.4,\n")
        with self.assertRaises(ValueError):
            load_rate_series(path)

    def test_loads_and_parses_option(self):
        path = self.write("# comment\neffective_date,rate,source\n2026-01-01,0.4,TCMB PPK\n")
        model = parse_cash_option(f"rate:{path},tax=0.1,spread=0.02")
        g = model.growth(T("2026-01-01"), T("2026-01-02"))
        self.assertAlmostEqual(g.factor, 1 + 0.38 * 0.9 / 365, places=12)
        self.assertIsNone(parse_cash_option("none"))
        self.assertAlmostEqual(parse_cash_option("fixed:0.3").annual_rate, 0.3)


if __name__ == "__main__":
    unittest.main()
