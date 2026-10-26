import unittest
from datetime import date

import numpy as np
import pandas as pd

from core.alerts.portfolio import evaluate_portfolio, portfolio_risk
from core.config import alerts as cfg

DAY = date(2026, 10, 26)


def frame(returns, start=100.0):
    index = pd.bdate_range(end="2026-10-26", periods=len(returns) + 1)
    close = start * np.cumprod(np.r_[1.0, 1 + np.asarray(returns)])
    return pd.DataFrame({"open": close, "high": close, "low": close, "close": close, "volume": 1e6}, index=index)


class PortfolioRiskTest(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(1)
        self.common = rng.normal(0, 0.02, 260)
        self.noise = rng.normal(0, 0.02, (3, 260))

    def test_var_matches_the_replayed_quantile(self):
        r = self.noise[0]
        risk = portfolio_risk({"A.IS": 50_000.0}, {"A.IS": frame(r)}, total=100_000)

        expected = -np.quantile(0.5 * r[-cfg.VAR_DAYS:], 0.05)
        self.assertAlmostEqual(risk.var, expected)
        self.assertEqual(risk.days, cfg.VAR_DAYS)
        self.assertIn("1 günlük kayıp", risk.line())

    def test_correlated_heavy_pair_is_flagged(self):
        a = self.common + 0.002 * self.noise[0]
        b = self.common + 0.002 * self.noise[1]
        c = self.noise[2]
        risk = portfolio_risk(
            {"A.IS": 25_000.0, "B.IS": 25_000.0, "C.IS": 20_000.0},
            {"A.IS": frame(a), "B.IS": frame(b), "C.IS": frame(c)},
            total=100_000,
        )

        self.assertEqual([(x, y) for x, y, _ in risk.pairs], [("A.IS", "B.IS")])
        alerts = evaluate_portfolio("paper", risk, DAY)
        self.assertEqual([a.rule for a in alerts], ["korelasyon"])
        self.assertIn("A+B", alerts[0].symbol)
        self.assertIn("en yüksek korelasyon A–B", risk.line())

    def test_light_pair_is_not_flagged(self):
        a = self.common + 0.002 * self.noise[0]
        b = self.common + 0.002 * self.noise[1]
        risk = portfolio_risk({"A.IS": 10_000.0, "B.IS": 10_000.0}, {"A.IS": frame(a), "B.IS": frame(b)}, 100_000)
        self.assertEqual(risk.pairs, [])
        self.assertGreater(risk.top_pair[2], cfg.CORR_HIGH)

    def test_big_loss_estimate_alerts(self):
        r = np.random.default_rng(2).normal(0, 0.06, 260)
        risk = portfolio_risk({"A.IS": 100_000.0}, {"A.IS": frame(r)}, total=100_000)
        self.assertGreater(risk.var, cfg.VAR_LIMIT)
        self.assertIn("portfoy_risk", [a.rule for a in evaluate_portfolio("paper", risk, DAY)])
        self.assertAlmostEqual(risk.effective_n, 1.0)

    def test_missing_price_is_reported_not_ignored(self):
        risk = portfolio_risk({"A.IS": float("nan"), "B.IS": 10_000.0}, {"B.IS": frame(self.noise[0])}, 50_000)
        self.assertIsNone(risk.var)
        self.assertIn("fiyatı olmayan: A", risk.line())
        alerts = evaluate_portfolio("real", risk, DAY)
        self.assertEqual([a.rule for a in alerts], ["fiyatsiz_pozisyon"])

    def test_short_history_is_unknown(self):
        risk = portfolio_risk({"A.IS": 10_000.0}, {"A.IS": frame(self.noise[0][:30])}, 100_000)
        self.assertIsNone(risk.var)
        self.assertIn("hesaplanamadı", risk.line())
        self.assertEqual(evaluate_portfolio("paper", risk, DAY), [])


if __name__ == "__main__":
    unittest.main()
