"""
Bağımsız doğrulama M28 (docs/validation/M28.md). YÜKSEK: /risk denge did not bring the real account
back within its limits — a sale shrinks the real account's total (46,3% fell only to 42,7% against
40%), and an equal cut leaves its weights and volatility unchanged. Every cut is now re-measured;
what selling cannot reach is said, not computed. ORTA: unmeasured rows were reported as "within the
limits", limit file problems were never shown, nan/inf limits were accepted.
"""

import tempfile
import unittest
from pathlib import Path

import numpy as np

from core.alerts import budget as B
from tests.test_risk_budget import BASE, frame


def setup(values_tl, paper, cash=0.0):
    frames = {s: frame(BASE * k) for s, k in zip(values_tl, (1, 2, 0.5, 1.5), strict=False)}
    prices = {s: float(df["close"].iloc[-1]) for s, df in frames.items()}
    quantities = {s: v / prices[s] for s, v in values_tl.items()}
    total = sum(values_tl.values()) + (cash if paper else 0.0)
    return frames, prices, quantities, total


class RebalanceTest(unittest.TestCase):
    def remeasure(self, frames, prices, quantities, total, cuts, paper, limits):
        values, total = B.after_cuts(quantities, prices, cuts, total, paper)
        return B.rows(B.measure(values, frames, total, frame(BASE)["close"]), limits)

    def test_real_account_single_stock_is_within_after_the_cut(self):
        limits = {"tek_hisse": 0.40}
        frames, prices, quantities, total = setup({"A.IS": 46_300.0, "B.IS": 30_000.0, "C.IS": 23_700.0}, paper=False)
        m = B.measure({s: quantities[s] * prices[s] for s in prices}, frames, total, frame(BASE)["close"])
        cuts = B.rebalance(m, limits, prices, quantities, paper=False)
        after = self.remeasure(frames, prices, quantities, total, cuts, False, limits)
        single = next(r for r in after if r.name == "tek_hisse")
        self.assertLessEqual(single.value, 0.40 + 1e-9)  # was 42,7% with the fixed-total formula

    def test_paper_account_volatility_is_within_after_the_cut(self):
        frames, prices, quantities, total = setup({"A.IS": 40_000.0, "B.IS": 40_000.0}, paper=True, cash=20_000.0)
        m = B.measure({s: quantities[s] * prices[s] for s in prices}, frames, total, frame(BASE)["close"])
        limits = {"oynaklik": m.volatility * 0.7}
        cuts = B.rebalance(m, limits, prices, quantities, paper=True)
        after = self.remeasure(frames, prices, quantities, total, cuts, True, limits)
        self.assertLessEqual(next(r for r in after if r.name == "oynaklik").value, limits["oynaklik"] + 1e-9)

    def test_real_account_volatility_is_said_not_computed(self):
        frames, prices, quantities, total = setup({"A.IS": 40_000.0, "B.IS": 40_000.0}, paper=False)
        m = B.measure({s: quantities[s] * prices[s] for s in prices}, frames, total, frame(BASE)["close"])
        limits = {"oynaklik": m.volatility * 0.7}
        self.assertEqual(B.rebalance(m, limits, prices, quantities, paper=False), {})  # equal cuts changed nothing
        notes = B.rebalance_notes(m, limits, paper=False)
        self.assertTrue(any("nakit" in n for n in notes))

    def test_too_few_real_stocks_for_the_single_limit(self):
        frames, prices, quantities, total = setup({"A.IS": 60_000.0, "B.IS": 40_000.0}, paper=False)
        m = B.measure({s: quantities[s] * prices[s] for s in prices}, frames, total, frame(BASE)["close"])
        limits = {"tek_hisse": 0.40}  # two stocks: the largest is at least 50%
        self.assertEqual(B.rebalance(m, limits, prices, quantities, paper=False), {})
        self.assertTrue(any("en az %50" in n for n in B.rebalance_notes(m, limits, paper=False)))

    def test_drawdown_cannot_be_sold_away(self):
        m = B.Measures(100_000.0, drawdown=0.30)
        self.assertTrue(any("düşüş" in n for n in B.rebalance_notes(m, {"dusus": 0.20}, paper=True)))
        text = B.rebalance_text("sanal", {}, {}, B.rebalance_notes(m, {"dusus": 0.20}, paper=True))
        self.assertNotIn("sınırların içinde", text)


class SummaryTest(unittest.TestCase):
    def test_unmeasured_limit_is_not_within(self):
        m = B.Measures(100_000.0, weights={"A.IS": 0.1}, unpriced=[])
        line = B.summary_line(B.rows(m, {"oynaklik": 0.30}))  # volatility not computed
        self.assertNotIn("sınırlar içinde", line)
        self.assertIn("ölçülemedi", line)

    def test_sector_only_is_not_within(self):
        m = B.Measures(100_000.0, weights={"A.IS": 0.1})
        self.assertNotIn("sınırlar içinde", B.summary_line(B.rows(m, {"tek_sektor": 0.30})))


class LimitFileTest(unittest.TestCase):
    def load(self, text, account="paper"):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "risk_limits.csv"
            path.write_text(text, encoding="utf-8")
            problems = []
            return B.load_limits(account, path, problems), problems

    def test_nan_inf_refused(self):
        limits, problems = self.load("account,limit,value,note\nhepsi,oynaklik,nan,\nhepsi,tek_hisse,inf,\n")
        self.assertEqual(limits, {})
        self.assertEqual(len(problems), 2)

    def test_semicolon_file_is_read(self):
        limits, problems = self.load("account;limit;value;note\nhepsi;tek_hisse;20;\n")
        self.assertEqual(limits, {"tek_hisse": 0.20})
        self.assertEqual(problems, [])

    def test_a_limit_written_twice_is_said(self):
        limits, problems = self.load("account,limit,value,note\nhepsi,tek_hisse,20,\nsanal,tek_hisse,25,\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("iki kez", problems[0])
        self.assertEqual(limits["tek_hisse"], 0.20)  # the stricter one

    def test_problems_reach_the_daily_line(self):
        from unittest import mock

        from core.reports import daily

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "risk_limits.csv"
            path.write_text("account,limit,value,note\nhepsi,oynaklik,abc,\n", encoding="utf-8")
            with mock.patch.object(B, "LIMITS_FILE", path):
                text, _ = daily._risk_budget("paper", {}, {}, 100_000.0, frame(BASE)["close"], None, None)
        self.assertIn("1 satır sorunlu", text)

    def test_problems_reach_the_table(self):
        from unittest import mock

        st = B.AccountState("paper", {}, {}, 100_000.0, frame(BASE)["close"], None, {}, {})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "risk_limits.csv"
            path.write_text("account,limit,value,note\nhepsi,oynaklik,abc,\n", encoding="utf-8")
            with mock.patch.object(B, "LIMITS_FILE", path), mock.patch.object(B, "account_state", return_value=st):
                text = B.command_text([])
        self.assertIn("okunamadı", text)


if __name__ == "__main__":
    np.random.seed(0)
    unittest.main()
