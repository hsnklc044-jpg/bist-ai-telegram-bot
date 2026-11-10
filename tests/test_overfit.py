"""K-81: Deflated Sharpe Ratio and PBO (CSCV) in the research report, information only. Written before the
functions and before any research result was looked at."""

import unittest

import numpy as np
import pandas as pd

from core.backtest import overfit


def noise(n_strategies, days=1600, seed=0, drift=None):
    rng = np.random.default_rng(seed)
    index = pd.bdate_range("2019-01-01", periods=days)
    data = rng.normal(0.0, 0.01, size=(days, n_strategies))
    if drift is not None:
        data[:, 0] += drift
    return {f"S{i}": pd.Series(data[:, i], index=index) for i in range(n_strategies)}


class DeflatedSharpeTest(unittest.TestCase):
    def test_one_strategy_is_not_computed(self):
        self.assertIsNone(overfit.deflated_sharpe(noise(1)))

    def test_a_clear_edge_survives_the_deflation(self):
        name, dsr, n = overfit.deflated_sharpe(noise(6, drift=0.002))
        self.assertEqual((name, n), ("S0", 6))
        self.assertGreater(dsr, 0.95)

    def test_the_best_of_pure_noise_is_not_convincing(self):
        _, dsr, _ = overfit.deflated_sharpe(noise(6, seed=3))
        self.assertLess(dsr, 0.9)

    def test_more_trials_lower_the_dsr_for_the_same_best(self):
        few = noise(3, drift=0.0006, seed=1)
        many = {**few, **{f"X{i}": s for i, s in enumerate(noise(30, seed=2).values())}}
        name_few, dsr_few, _ = overfit.deflated_sharpe(few)
        name_many, dsr_many, n = overfit.deflated_sharpe(many)
        self.assertEqual((name_few, name_many, n), ("S0", "S0", 33))
        self.assertLess(dsr_many, dsr_few)

    def test_flat_series_do_not_crash(self):
        index = pd.bdate_range("2020-01-01", periods=300)
        flat = {"A": pd.Series(0.0, index=index), "B": pd.Series(0.0, index=index)}
        self.assertIsNone(overfit.deflated_sharpe(flat))


class PboTest(unittest.TestCase):
    def test_pure_noise_is_about_a_coin_toss(self):
        value = overfit.pbo(noise(10, seed=4))
        self.assertGreater(value, 0.3)
        self.assertLess(value, 0.7)

    def test_a_dominant_strategy_is_rarely_overfit(self):
        self.assertLess(overfit.pbo(noise(6, drift=0.003)), 0.05)

    def test_too_few_strategies_or_days_are_not_computed(self):
        self.assertIsNone(overfit.pbo(noise(1)))
        self.assertIsNone(overfit.pbo(noise(4, days=16 * 5 - 1)))
        self.assertIsNotNone(overfit.pbo(noise(4, days=16 * 5)))

    def test_the_split_count_is_16_choose_8(self):
        self.assertEqual(overfit.SPLITS, 12870)


class ReportLineTest(unittest.TestCase):
    def test_the_line_says_information_only_and_names_both(self):
        equities = {k: (1 + s).cumprod() * 100 for k, s in noise(6, drift=0.002).items()}
        line = overfit.report_line(equities)
        self.assertTrue(line.startswith("Aşırı uyum (bilgi, K-81; karar değişmez): en yüksek Sharpe S0"))
        self.assertRegex(line, r"DSR %\d+ \(6 strateji\) · PBO %\d+ \(CSCV, 16 blok\)")

    def test_unusable_input_is_said(self):
        index = pd.bdate_range("2020-01-01", periods=10)
        line = overfit.report_line({"A": pd.Series(100.0, index=index)})
        self.assertIn("hesaplanmadı", line)

    def test_only_common_days_are_used(self):
        a = noise(3, days=400, seed=5)
        short = {k: (1 + s.iloc[100:]).cumprod() for k, s in a.items()}
        short["S0"] = (1 + a["S0"]).cumprod()  # longer than the others
        self.assertEqual(len(overfit.returns_matrix(short)), 299)


if __name__ == "__main__":
    unittest.main()
