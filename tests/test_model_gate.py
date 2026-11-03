"""
K-70 madde 5 (ModelGovernor): a high-risk model may change something on its own only with a current
independent validation whose verdict is "kullanılabilir". Restricted, unusable, expired or
unvalidated models only inform. The decision is shown in /durum.
"""

import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from core.reports import model_gate as G

TODAY = date(2026, 11, 4)


class DecisionTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def report(self, code, day, verdict):
        (self.dir / f"{code}.md").write_text(f"# {code}\nTarih: {day}\nKarar: {verdict}\n", encoding="utf-8")

    def decide(self, code):
        return G.decide(code, TODAY, self.dir)

    def test_only_a_current_usable_verdict_opens_the_gate(self):
        self.report("M30", "2026-10-30", "kullanılabilir")
        d = self.decide("M30")
        self.assertTrue(d.allowed, d.reason)

    def test_everything_else_stays_closed(self):
        self.assertIn("bağımsız doğrulanmadı", self.decide("M30").reason)
        self.assertFalse(self.decide("M30").allowed)
        self.report("M30", "2026-10-30", "kısıtlı kullanılabilir")
        self.assertFalse(self.decide("M30").allowed)
        self.assertIn("kısıtlı", self.decide("M30").reason)
        self.report("M30", "2026-10-30", "kullanılamaz")
        self.assertFalse(self.decide("M30").allowed)
        self.report("M30", "2025-10-01", "kullanılabilir")  # older than a year
        self.assertFalse(self.decide("M30").allowed)
        self.assertIn("süresi geçmiş", self.decide("M30").reason)

    def test_a_model_that_is_not_high_risk_is_not_gated(self):
        self.assertTrue(G.decide("M23", TODAY, self.dir).allowed)

    def test_durum_line_names_every_automatic_action(self):
        self.report("M30", "2026-10-30", "kısıtlı kullanılabilir")
        state, text = G.status(TODAY, self.dir)
        self.assertEqual(state, "info")
        for code in G.AUTO_ACTIONS:
            self.assertIn(code, text)
        self.assertIn("kapalı", text)


class DailyStepTest(unittest.TestCase):
    def test_the_daily_step_asks_the_gate(self):
        # the ML filter reports a pass, but M30 has no independent validation: nothing is recorded
        from core.signals import daily as book

        closed = G.Decision("M30", False, "bağımsız doğrulanmadı")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "signals.db"
            with mock.patch("core.ml.ml_filter.enabled", return_value=True), \
                    mock.patch.object(G, "decide", return_value=closed), \
                    mock.patch("core.signals.panic.active", return_value=False):
                self.assertFalse(book.filter_on(date(2026, 11, 4)))
                text = book.run(date(2026, 11, 4), lambda s: None, None, path)
            self.assertEqual(text, "")
            self.assertFalse(path.exists())
            with mock.patch("core.ml.ml_filter.enabled", return_value=True), \
                    mock.patch.object(G, "decide", return_value=G.Decision("M30", True, "ok")):
                self.assertTrue(book.filter_on(date(2026, 11, 4)))
