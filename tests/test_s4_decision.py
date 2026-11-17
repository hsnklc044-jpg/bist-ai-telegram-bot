"""K-93 (1), (2), (4): the live first decision, its RESEARCH_LOG draft and the S5 notice, on synthetic data."""

import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from core.reports import s4_decision as s4
from core.reports.forward import VIEW_ORDER


def _days(n):
    start = date(2026, 10, 23)
    return [start + timedelta(days=i) for i in range(n)]


def scored(n_days=46, excess=None, views=VIEW_ORDER, horizon=5):
    """One record per view and day; `excess(view, i)` gives the result (default alternating ±1%)."""

    excess = excess or (lambda view, i: 0.01 if i % 2 else -0.01)
    rows = [{"source": "daily", "view": v, "day": d, "horizon": horizon, "excess": excess(v, i), "symbol": "AAA"}
            for i, d in enumerate(_days(n_days)) for v in views]
    return pd.DataFrame(rows)


class FirstDecisionTest(unittest.TestCase):
    def test_no_decision_until_every_view_is_mature(self):
        self.assertIsNone(s4.first_decision(scored(45), {}))          # 45 days: 9 independent periods
        self.assertIsNone(s4.first_decision(scored(46, views=VIEW_ORDER[:4]), {}))  # one view missing

    def test_decision_uses_the_unchanged_forward_verdict(self):
        d = s4.first_decision(scored(46), {})
        self.assertIsNotNone(d)
        self.assertEqual(d["horizon"], 5)
        self.assertEqual(len(d["views"]), 5)
        for v in d["views"]:
            self.assertEqual(v["verdict"], "XU100'den farkı anlamlı değil")
            self.assertEqual(v["periods"], 10)
        self.assertEqual(d["rule"], "K-93 (1)")

    def test_secondary_horizons_do_not_decide(self):
        frame = pd.concat([scored(46, horizon=20)])
        self.assertIsNone(s4.first_decision(frame, {}))

    def test_drift_against_reference_is_written(self):
        ref = {(v, 5): {"mean": 0.20, "hit_rate": 0.5} for v in VIEW_ORDER}
        d = s4.first_decision(scored(46), ref, reasons=lambda rows, r: ["en etkili 3 hisse olmadan: sürüyor"])
        self.assertTrue(all("sapma" in v["drift"] for v in d["views"]))
        self.assertEqual(d["views"][0]["reasons"], ["en etkili 3 hisse olmadan: sürüyor"])


class S5ThresholdTest(unittest.TestCase):
    def test_t99_matches_scipy(self):
        try:
            from scipy import stats
        except ImportError:  # pragma: no cover
            self.skipTest("scipy yok")
        for df in range(1, 31):
            self.assertAlmostEqual(s4.T99[df - 1], stats.t.ppf(0.995, df), places=2)

    def test_hand_computed_threshold(self):
        d = s4.first_decision(scored(46, excess=lambda v, i: 0.02), {})
        # constant +2%: sd 0, so low99 = 0.02 - 0.003 > 0 for every view
        self.assertEqual([v["view"] for v in s4.s5_passing(d)], list(VIEW_ORDER))
        v = d["views"][0]
        self.assertAlmostEqual(v["low99_after_cost"], 0.02 - s4.ROUND_TRIP_COST)

    def test_cost_alone_blocks(self):
        d = s4.first_decision(scored(46, excess=lambda v, i: 0.002), {})  # +0.2% < 0.3% cost
        self.assertEqual(s4.s5_passing(d), [])

    def test_95_significant_is_not_enough(self):
        # alternate +3% / +0.5% on apart days: 95% low > 0 but 99% low after cost < 0
        def ex(v, i):
            return 0.03 if (i // 5) % 2 else 0.001
        d = s4.first_decision(scored(46, excess=ex), {})
        v = d["views"][0]
        self.assertEqual(v["verdict"], "XU100'ü anlamlı şekilde geçiyor")
        self.assertLess(v["low99_after_cost"], 0)
        self.assertEqual(s4.s5_passing(d), [])

    def test_cost_matches_trading_config(self):
        from core.config.trading import COMMISSION, SLIPPAGE

        self.assertAlmostEqual(s4.ROUND_TRIP_COST, 2 * (COMMISSION + SLIPPAGE))


class CheckTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.paths = dict(decision=self.dir / "s4_ilk_karar.json", drafts=self.dir / "taslak",
                          notice=self.dir / "s5_bildirim.json")

    def run_check(self, frame, day=date(2027, 1, 6)):
        return s4.check(day, frame, {}, **self.paths)

    def test_nothing_before_maturity(self):
        self.assertEqual(self.run_check(scored(40)), [])
        self.assertFalse(self.paths["decision"].exists())
        self.assertFalse(self.paths["drafts"].exists())

    def test_first_decision_written_once_with_draft(self):
        msgs = self.run_check(scored(46))
        self.assertEqual(len(msgs), 1)
        self.assertIn("S4 canlı ölçüm: ilk karar", msgs[0])
        saved = json.loads(self.paths["decision"].read_text(encoding="utf-8"))
        self.assertEqual(saved["date"], "2027-01-06")
        draft = next(self.paths["drafts"].glob("*.md")).read_text(encoding="utf-8")
        self.assertIn("## 06.01.2027 – Canlı ölçüm ilk kararı (K-93)", draft)
        for field in ("Soru", "Veri", "Ölçüt", "Sonuç", "Backtest–canlı sapması", "Deneme sayısı"):
            self.assertIn(field, draft)
        # later evenings do not rewrite the decision, even when the data changed
        self.assertEqual(self.run_check(scored(60, excess=lambda v, i: 0.01 if i % 3 else -0.02),
                                        date(2027, 1, 20)), [])
        self.assertEqual(json.loads(self.paths["decision"].read_text(encoding="utf-8")), saved)

    def test_s5_notice_once_with_evidence_and_opens_nothing(self):
        before = sorted(p.name for p in self.dir.iterdir())
        msgs = self.run_check(scored(46, excess=lambda v, i: 0.02))
        self.assertEqual(len(msgs), 2)
        notice = msgs[1]
        self.assertIn("Kural anlamlı çıktı", notice)
        self.assertIn("%99", notice)
        self.assertIn("maliyet", notice)
        self.assertIn("hiçbir şey açılmadı", notice)
        self.assertEqual(self.run_check(scored(47, excess=lambda v, i: 0.02), date(2027, 1, 7)), [])
        written = sorted(p.name for p in self.dir.iterdir())
        self.assertEqual(sorted(set(written) - set(before)), ["s4_ilk_karar.json", "s5_bildirim.json", "taslak"])


if __name__ == "__main__":
    unittest.main()
