"""
Look-ahead guard.

If any rule, filter or the engine used information from after day T,
then changing the prices after T would change what happened up to T.
Each test scrambles the future and checks that the past is identical.

Two variants:
- scrambled: same dates, different future prices
- truncated: the future does not exist yet (as in live use)
"""

import unittest

import numpy as np
import pandas as pd

from core.backtest.engine import BacktestConfig, run_backtest
from core.strategy.filters import apply_eligibility, eligibility
from core.strategy.rules import (
    apply_rule,
    index_trend_signals,
    low_volatility_signals,
    momentum_signals,
    regime_filter,
    score_rule,
    trend_rule,
    turn_of_month_signals,
    with_regime,
)
from core.strategy.score import score_frame
from tests.golden import load_prices

CUTS = (260, 330, 400)


def scramble(frames: dict[str, pd.DataFrame], cut_day: pd.Timestamp, seed: int = 7):
    """Multiply every price after cut_day by an independent random path."""

    rng = np.random.default_rng(seed)
    out = {}
    for symbol, df in frames.items():
        df = df.copy()
        future = df.index > cut_day
        n = int(future.sum())
        if n:
            shock = np.exp(np.cumsum(rng.normal(0, 0.05, n)))
            for col in ("open", "high", "low", "close"):
                df.loc[future, col] = df.loc[future, col].to_numpy() * shock
            df.loc[future, "volume"] = df.loc[future, "volume"].to_numpy() * rng.uniform(0.1, 10, n)
        out[symbol] = df
    return out


def truncate(frames: dict[str, pd.DataFrame], cut_day: pd.Timestamp):
    return {s: df[df.index <= cut_day] for s, df in frames.items()}


class NoLookaheadTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frames, cls.bench = load_prices()
        cls.dates = cls.frames["S01"].index

    def variants(self):
        for i in CUTS:
            cut = self.dates[i]
            frames_s = scramble(self.frames, cut)
            bench_s = scramble({"B": self.bench}, cut, seed=11)["B"]
            yield cut, "scrambled", frames_s, bench_s
            yield cut, "truncated", truncate(self.frames, cut), self.bench[self.bench.index <= cut]

    def assert_past_equal(self, a: pd.DataFrame | pd.Series, b, cut, label):
        a = a[a.index <= cut]
        b = b[b.index <= cut]
        pd.testing.assert_frame_equal(
            a.to_frame() if isinstance(a, pd.Series) else a,
            b.to_frame() if isinstance(b, pd.Series) else b,
            check_freq=False,
            obj=label,
        )

    def check_signals(self, build, name, truncation_ok=True):
        base = build(self.frames, self.bench)
        for cut, kind, frames, bench in self.variants():
            if kind == "truncated" and not truncation_ok:
                continue
            with self.subTest(rule=name, cut=str(cut.date()), kind=kind):
                other = build(frames, bench)
                for symbol in base:
                    self.assert_past_equal(base[symbol], other[symbol], cut, f"{name}/{symbol}")

    def test_score_frame(self):
        self.check_signals(
            lambda f, b: {s: score_frame(df) for s, df in f.items()}, "score_frame"
        )

    def test_score_rule(self):
        self.check_signals(lambda f, b: apply_rule(score_rule(70, 60), f), "score_rule")

    def test_trend_rule(self):
        self.check_signals(lambda f, b: apply_rule(trend_rule(10, 30, 100), f), "trend_rule")

    def test_regime_filter(self):
        self.check_signals(lambda f, b: {"XU100": regime_filter(b, 100)}, "regime_filter")

    def test_trend_with_regime_and_eligibility(self):
        def build(f, b):
            signals = with_regime(apply_rule(trend_rule(10, 30, 100), f), regime_filter(b, 100))
            ok = eligibility(f, liquidity_top=8, max_run_up=0.5, run_up_window=63, max_locks=1)
            return apply_eligibility(signals, ok, exit_when_ineligible=True)

        self.check_signals(build, "trend+regime+eligibility")

    def test_momentum_scrambled(self):
        self.check_signals(
            lambda f, b: momentum_signals(f, 63, 10, 4, regime=regime_filter(b, 100)),
            "momentum",
            truncation_ok=False,
        )

    def test_low_volatility_scrambled(self):
        # Aşama 3 H1; like momentum, a truncated history makes the cut day a month end
        self.check_signals(lambda f, b: low_volatility_signals(f, 60, 4), "low_volatility", truncation_ok=False)

    def test_index_trend(self):
        # Aşama 3 H2; months are timed by the session calendar, so a truncated history must agree too
        self.check_signals(lambda f, b: {"XU100": index_trend_signals(b, 100)}, "index_trend")

    def test_turn_of_month(self):
        # Aşama 3 H3
        self.check_signals(lambda f, b: {"XU100": turn_of_month_signals(b, 3)}, "turn_of_month")

    def test_engine(self):
        config = BacktestConfig(max_positions=5, atr_stop=2.0, max_holding_days=40)
        start = self.dates[220]
        base = run_backtest(self.frames, trend_rule(10, 30, 100), config, start=start)
        for cut, kind, frames, _ in self.variants():
            with self.subTest(cut=str(cut.date()), kind=kind):
                other = run_backtest(frames, trend_rule(10, 30, 100), config, start=start)
                self.assert_past_equal(base.equity, other.equity, cut, "equity")

                def entries(result):
                    # order-independent: trades opened on the same day may be
                    # listed in a different order when the run ends earlier
                    return sorted(
                        (t.entry_date, t.symbol, round(t.entry_price, 10), round(t.shares, 10))
                        for t in result.trades
                        if t.entry_date <= cut
                    )

                self.assertEqual(entries(base), entries(other))


class MonthEndRebalanceTest(unittest.TestCase):
    """
    Momentum rebalances on the last session of each month. With
    truncated data the newest day is not known to be a month end, so a
    live run and the backtest agree on every day except possibly the
    newest one. This test documents that the difference is limited to
    the newest day.
    """

    def test_only_newest_day_can_differ(self):
        frames, bench = load_prices()
        dates = frames["S01"].index
        base = momentum_signals(frames, 63, 10, 4, regime=regime_filter(bench, 100))
        for i in CUTS:
            cut = dates[i]
            live = momentum_signals(
                truncate(frames, cut), 63, 10, 4, regime=regime_filter(bench[bench.index <= cut], 100)
            )
            before = dates[i - 1]
            for symbol in base:
                pd.testing.assert_frame_equal(
                    base[symbol][base[symbol].index <= before],
                    live[symbol][live[symbol].index <= before],
                    check_freq=False,
                )


class CandidateRulesNoLookaheadTest(NoLookaheadTest):
    """The research candidates must pass the same guard (scrambled and truncated futures)."""

    def test_candidates(self):
        from core.strategy.candidates import CANDIDATES

        for name, (factory, grid) in CANDIDATES.items():
            for params in grid:
                self.check_signals(lambda f, b, fac=factory, p=params: apply_rule(fac(**p), f), f"{name}{params}")

    def test_weekly_values_use_completed_weeks_only(self):
        from core.strategy.candidates import weekly_values

        close = self.frames["S01"]["close"]
        values = weekly_values(close, lambda w: w)
        friday = close.index[close.index.day_of_week == 4][10]
        monday = friday + pd.Timedelta(days=3)
        previous_friday = friday - pd.Timedelta(days=7)
        # during the week (Friday included) the last COMPLETED week is used;
        # the week is used from the next trading day on
        self.assertEqual(values.loc[friday], close.loc[previous_friday])
        self.assertEqual(values.loc[monday], close.loc[friday])


if __name__ == "__main__":
    unittest.main()
