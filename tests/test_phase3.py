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


if __name__ == "__main__":
    unittest.main()
