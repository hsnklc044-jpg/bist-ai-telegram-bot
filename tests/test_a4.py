"""a4 (RESEARCH_LOG "a4 ön kaydı", 28.10.2026): H4 equal weight and H5 low turnover, judged as
pre-registered. Synthetic data only: no result on real prices is computed before 27.04.2027."""

import unittest
from datetime import date
from unittest import mock

import numpy as np
import pandas as pd

from core.backtest import a4
from core.strategy.rules import equal_weight_signals, low_turnover_signals


def _frame(close, volume=1e7):
    return pd.DataFrame({"open": close, "high": close, "low": close, "close": close, "volume": volume},
                        index=close.index)


class LowTurnoverTest(unittest.TestCase):
    def setUp(self):
        index = pd.bdate_range("2024-01-01", "2024-06-28")
        self.index = index
        close = pd.Series(10.0, index=index)
        # TL turnover = close x volume: A 10 x 100, B 10 x 1000, C 10 x 10 (lowest)
        self.frames = {"A.IS": _frame(close, 100.0), "B.IS": _frame(close, 1000.0), "C.IS": _frame(close, 10.0)}

    def test_lowest_median_turnover_is_held_from_the_month_end(self):
        signals = low_turnover_signals(self.frames, window=60, top_n=1)
        day = pd.Timestamp("2024-03-29")  # first month end with 60 sessions behind it (65)
        self.assertTrue(signals["C.IS"].loc[day, "enter"])
        self.assertFalse(signals["A.IS"].loc[day, "enter"])
        self.assertFalse(signals["C.IS"].loc[pd.Timestamp("2024-02-29"), "enter"])  # 44 sessions: not yet

    def test_no_look_ahead(self):
        day = pd.Timestamp("2024-04-30")
        before = {s: low_turnover_signals(self.frames, 60, 1)[s].loc[day, "enter"] for s in self.frames}
        changed = dict(self.frames)
        late = self.frames["B.IS"].copy()
        late.loc[late.index > day, "volume"] = 0.001  # B becomes the quietest only AFTER the choice
        changed["B.IS"] = late
        after = {s: low_turnover_signals(changed, 60, 1)[s].loc[day, "enter"] for s in self.frames}
        self.assertEqual(before, after)

    def test_only_eligible_stocks(self):
        eligible = pd.DataFrame(True, index=self.index, columns=list(self.frames))
        eligible["C.IS"] = False
        signals = low_turnover_signals(self.frames, 60, 1, eligible=eligible)
        self.assertTrue(signals["A.IS"].loc[pd.Timestamp("2024-04-30"), "enter"])


class EqualWeightTest(unittest.TestCase):
    def test_every_eligible_stock_with_a_price(self):
        index = pd.bdate_range("2024-01-01", "2024-03-29")
        frames = {s: _frame(pd.Series(10.0, index=index)) for s in ("A.IS", "B.IS", "C.IS")}
        eligible = pd.DataFrame(True, index=index, columns=list(frames))
        eligible.loc[eligible.index >= "2024-02-15", "B.IS"] = False  # left the index
        signals = equal_weight_signals(frames, eligible)
        jan, feb = pd.Timestamp("2024-01-31"), pd.Timestamp("2024-02-29")
        self.assertTrue(all(signals[s].loc[jan, "enter"] for s in frames))
        self.assertEqual([s for s in frames if signals[s].loc[feb, "enter"]], ["A.IS", "C.IS"])


def market(bench_drift: float):
    """12 quiet, cheaply traded stocks drifting up, 8 busy ones with no drift, plus XU100."""

    index = pd.bdate_range("2023-01-02", "2025-12-31")
    rng = np.random.default_rng(7)
    frames = {}
    for i in range(20):
        quiet = i < 12
        drift, volume = (0.0015, 1e5) if quiet else (0.0, 1e8)
        close = 100 * np.exp(np.cumsum(rng.normal(drift, 0.01, len(index))))
        frames[f"S{i:02d}.IS"] = _frame(pd.Series(close, index=index), volume)
    xu = 100 * np.exp(np.cumsum(rng.normal(bench_drift, 0.01, len(index))))
    eligible = pd.DataFrame(True, index=index, columns=list(frames))
    return frames, _frame(pd.Series(xu, index=index)), eligible


class GatesTest(unittest.TestCase):
    def test_h5_accepted_when_quiet_stocks_beat_a_falling_index(self):
        result = a4.evaluate(a4.H5, *market(bench_drift=-0.0005))
        self.assertEqual(set(result["gates"]), {"primary", "both_starts", "without_best", "drawdown", "double_cost"})
        self.assertTrue(all(result["gates"].values()), result["gates"])
        self.assertAlmostEqual(result["level"], 1 - 0.05 / 2)  # Bonferroni for the 2 registered hypotheses
        self.assertIn("KARAR: kabul", a4.report(result))

    def test_h4_has_no_double_cost_gate_and_is_rejected_by_a_runaway_index(self):
        result = a4.evaluate(a4.H4, *market(bench_drift=0.004))
        self.assertNotIn("double_cost", result["gates"])
        self.assertFalse(result["gates"]["primary"])
        self.assertIn("KARAR: red", a4.report(result))

    def test_record_is_its_own_family(self):
        result = a4.evaluate(a4.H5, *market(bench_drift=-0.0005))
        (row,) = a4.records(result)
        self.assertEqual((row["universe"], row["strategy"]), ("a4", a4.H5.name))
        self.assertEqual(row["period_start"][:7], "2023-08")


class DateGateTest(unittest.TestCase):
    def test_closed_before_the_registered_date_and_loads_no_prices(self):
        with mock.patch.object(a4, "_universe") as universe:
            text = a4.run(date(2027, 4, 26))
        universe.assert_not_called()
        self.assertIn("27.04.2027", text)
        self.assertIn("çalıştırılmadı", text)

    def test_open_from_the_registered_date(self):
        frames, bench, eligible = market(bench_drift=-0.0005)
        with mock.patch.object(a4, "_universe", return_value=(frames, None, eligible)), \
                mock.patch.object(a4, "load_frames", return_value={a4.BENCHMARK: bench}):
            text = a4.run(date(2027, 4, 27))
        self.assertIn(a4.H4.name, text)
        self.assertIn(a4.H5.name, text)


if __name__ == "__main__":
    unittest.main()
