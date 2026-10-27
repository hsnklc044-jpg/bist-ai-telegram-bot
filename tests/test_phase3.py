"""Aşama 3 evaluator: the pre-registered gates decide, exactly as RESEARCH_LOG fixed them."""

import unittest

import numpy as np
import pandas as pd

from core.backtest import phase3


def _frame(close):
    return pd.DataFrame({"open": close, "high": close, "low": close, "close": close, "volume": 1e7},
                        index=close.index)


def market(bench_drift: float):
    """12 calm stocks drifting up 0.15%/day and 8 wild ones with no drift, plus XU100."""

    index = pd.bdate_range("2023-01-02", "2025-12-31")
    rng = np.random.default_rng(7)
    frames = {}
    for i in range(20):
        calm = i < 12
        sigma, drift = (0.004, 0.0015) if calm else (0.04, 0.0)
        close = 100 * np.exp(np.cumsum(rng.normal(drift, sigma, len(index))))
        frames[f"S{i:02d}.IS"] = _frame(pd.Series(close, index=index))
    xu = 100 * np.exp(np.cumsum(rng.normal(bench_drift, 0.01, len(index))))
    eligible = pd.DataFrame(True, index=index, columns=list(frames))
    return frames, _frame(pd.Series(xu, index=index)), eligible


class GatesTest(unittest.TestCase):
    def test_all_gates_pass_when_calm_stocks_beat_a_falling_index(self):
        result = phase3.evaluate(*market(bench_drift=-0.0005))
        self.assertTrue(all(result["gates"].values()), result["gates"])
        self.assertAlmostEqual(result["level"], 1 - 0.05 / 3)  # Bonferroni for the 3 registered hypotheses
        self.assertEqual(len(result["best"]), 5)
        self.assertTrue(all(s.startswith("S") and int(s[1:3]) < 12 for s in result["best"]))  # calm ones were held
        self.assertIn("KARAR: kabul", phase3.report(result))

    def test_rejected_when_the_index_runs_away(self):
        result = phase3.evaluate(*market(bench_drift=0.004))
        self.assertFalse(result["gates"]["primary"])
        self.assertFalse(result["gates"]["both_starts"])
        self.assertIn("KARAR: red", phase3.report(result))

    def test_record_is_its_own_family(self):
        result = phase3.evaluate(*market(bench_drift=-0.0005))
        (row,) = phase3.records(result)
        self.assertEqual(row["universe"], "a3")
        self.assertEqual(row["period_start"][:7], "2023-08")  # first registered start
        self.assertEqual(row["strategy"], phase3.NAME)
        self.assertAlmostEqual(row["level"], 1 - 0.05 / 3)



def flat_cash(rate):
    from core.backtest.cash import RateSeries

    return RateSeries(pd.Series([rate], index=[pd.Timestamp("2020-01-01")]))


def index_market(daily):
    """XU100 with a given daily log return per calendar year: {2023: r, 2024: r, ...}."""

    index = pd.bdate_range("2022-01-03", "2026-10-23")
    rng = np.random.default_rng(1)
    drift = np.array([daily[d.year] for d in index])
    close = 100 * np.exp(np.cumsum(drift + rng.normal(0, 0.002, len(index))))
    return _frame(pd.Series(close, index=index))


class IndexRuleTest(unittest.TestCase):
    """H2/H3 (plan change 1): cash at the policy rate; the verdict must also hold at the rate minus 3 points."""

    def test_cash_beats_a_falling_index_and_strict_cash_is_checked(self):
        bench = index_market({2022: 0.002, 2023: -0.002, 2024: -0.002, 2025: -0.002, 2026: -0.002})
        result = phase3.evaluate_index(phase3.H2, bench, flat_cash(0.45), flat_cash(0.42))
        self.assertTrue(all(result["gates"].values()), result["gates"])
        self.assertTrue(all(result["strict_gates"].values()), result["strict_gates"])
        self.assertEqual(result["years"], (4, 4))  # 2023 (from 1 Aug) … 2026
        self.assertIn("KARAR: kabul", phase3.report_index(result))

    def test_strict_cash_can_reject_alone(self):
        bench = index_market({2022: 0.002, 2023: -0.002, 2024: -0.002, 2025: -0.002, 2026: -0.002})
        result = phase3.evaluate_index(phase3.H2, bench, flat_cash(0.45), flat_cash(-2.0))  # cash loses money
        self.assertTrue(all(result["gates"].values()))
        self.assertFalse(all(result["strict_gates"].values()))
        self.assertIn("KARAR: red", phase3.report_index(result))

    def test_rising_index_rejects_turn_of_month(self):
        bench = index_market({y: 0.003 for y in range(2022, 2027)})
        result = phase3.evaluate_index(phase3.H3, bench, flat_cash(0.0), flat_cash(0.0))
        self.assertFalse(result["gates"]["both_starts"])
        self.assertIn("KARAR: red", phase3.report_index(result))

    def test_records_name_the_cash(self):
        bench = index_market({y: 0.0 for y in range(2022, 2027)})
        result = phase3.evaluate_index(phase3.H3, bench, flat_cash(0.45), flat_cash(0.42), zero_cash_too=True)
        self.assertIn("bilgi: nakit %0", phase3.report_index(result))
        rows = phase3.index_records(result)
        self.assertEqual([r["universe"] for r in rows], ["a3", "a3"])
        self.assertEqual(rows[0]["strategy"], phase3.H3.name)
        self.assertIn("−3 puan", rows[1]["strategy"])


if __name__ == "__main__":
    unittest.main()
