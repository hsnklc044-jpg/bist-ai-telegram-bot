import unittest

import pandas as pd

from core.backtest.rotation import RotationConfig, current_picks, rotate
from tests.helpers import make_ohlcv

NO_COSTS = dict(commission=0.0, slippage=0.0)


def _prices(closes: dict[str, list[float]]) -> dict[str, pd.DataFrame]:
    index = pd.bdate_range("2026-01-05", periods=len(next(iter(closes.values()))))
    out = {}

    for symbol, values in closes.items():
        df = pd.DataFrame({"open": values, "close": values}, index=index, dtype=float)
        out[symbol] = df.dropna()

    return out


def _scores(prices, scores: dict[str, list[float]]):
    return {
        s: pd.DataFrame({"score": scores[s]}, index=next(iter(prices.values())).index)
        .reindex(df.index)
        for s, df in prices.items()
    }


class RotationTest(unittest.TestCase):
    def test_buys_best_ranked_at_next_open(self):
        prices = _prices({"A": [10, 10, 20, 20], "B": [10, 10, 10, 10]})
        signals = _scores(prices, {"A": [90] * 4, "B": [10] * 4})
        config = RotationConfig(top_n=1, ranking="score", rebalance_days=100, **NO_COSTS)

        result = rotate(prices, signals, config)

        self.assertEqual(result.rebalances[0].date, prices["A"].index[1])
        self.assertEqual(result.holdings, ["A"])
        self.assertEqual(list(result.equity), [1.0, 1.0, 2.0, 2.0])

    def test_switches_and_charges_only_traded_value(self):
        prices = _prices({"A": [10] * 6, "B": [10] * 6})
        signals = _scores(prices, {"A": [90, 90, 10, 10, 10, 10], "B": [10, 10, 90, 90, 90, 90]})
        config = RotationConfig(top_n=1, ranking="score", rebalance_days=2,
                                commission=0.01, slippage=0.0)

        result = rotate(prices, signals, config)

        self.assertEqual([r.holdings for r in result.rebalances], [["A"], ["B"], ["B"]])
        # buy A (1.0 traded), switch A->B (2 x 0.99 traded), then nothing to trade
        self.assertAlmostEqual(result.rebalances[2].turnover, 0.0)
        self.assertAlmostEqual(result.equity.iloc[-1], 0.99 - 2 * 0.99 * 0.01)
        self.assertEqual(result.trades, 2)

    def test_regime_filter_goes_to_cash(self):
        prices = _prices({"A": [10, 10, 5, 5]})
        signals = _scores(prices, {"A": [90] * 4})
        config = RotationConfig(top_n=1, ranking="score", rebalance_days=1,
                                regime_filter=True, **NO_COSTS)
        uptrend = pd.Series(False, index=prices["A"].index)

        result = rotate(prices, signals, config, uptrend)

        self.assertEqual(result.equity.iloc[-1], 1.0)
        self.assertEqual(result.exposure, 0.0)

    def test_stock_is_not_bought_before_it_trades(self):
        prices = _prices({"A": [10, 10, 10, 10], "NEW": [None, None, 10, 30]})
        signals = _scores(prices, {"A": [10] * 4, "NEW": [90] * 4})
        config = RotationConfig(top_n=1, ranking="score", rebalance_days=1, **NO_COSTS)

        result = rotate(prices, signals, config)

        self.assertEqual(result.rebalances[0].holdings, ["A"])
        self.assertEqual(result.rebalances[-1].holdings, ["NEW"])

    def test_future_prices_do_not_change_the_past(self):
        from core.backtest.signals import score_history

        prices = {f"S{i}": make_ohlcv(rows=500, seed=i) for i in range(6)}
        signals = {s: score_history(df) for s, df in prices.items()}
        cut = {s: df.iloc[:400] for s, df in prices.items()}
        cut_signals = {s: score_history(df) for s, df in cut.items()}

        full = rotate(prices, signals)
        part = rotate(cut, cut_signals)

        pd.testing.assert_series_equal(full.equity.iloc[:399], part.equity.iloc[:399])
        self.assertEqual(
            [(r.date, r.holdings) for r in full.rebalances if r.date <= cut["S0"].index[398]],
            [(r.date, r.holdings) for r in part.rebalances if r.date <= cut["S0"].index[398]],
        )

    def test_monthly_rebalance_after_first_session_of_month(self):
        index = pd.bdate_range("2026-01-26", "2026-03-06")
        prices = {"A": pd.DataFrame({"open": 10.0, "close": 10.0}, index=index)}
        signals = {"A": pd.DataFrame({"score": 90.0}, index=index)}
        config = RotationConfig(top_n=1, ranking="score", **NO_COSTS)

        result = rotate(prices, signals, config)

        self.assertEqual(
            [r.date for r in result.rebalances],
            [pd.Timestamp(d) for d in ("2026-01-27", "2026-02-03", "2026-03-03")],
        )

    def test_current_picks_ranked(self):
        prices = _prices({"A": [10, 10], "B": [10, 10]})
        signals = _scores(prices, {"A": [40, 40], "B": [80, 80]})

        picks = current_picks(prices, signals, RotationConfig(ranking="score"))

        self.assertEqual(list(picks.index), ["B", "A"])


if __name__ == "__main__":
    unittest.main()
