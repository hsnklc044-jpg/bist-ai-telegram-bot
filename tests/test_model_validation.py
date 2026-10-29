"""
Talimat F §F5–F6 (DECISIONS K-58): /durum shows how many high-risk models have an independent
validation report (docs/validation/<model>.md with "Tarih:" and "Karar:" lines). A report older
than a year (high risk) or two years (medium) is a warning; none yet is information.
"""

import tempfile
import unittest
from datetime import date
from pathlib import Path

from core.reports import validation as V


class RegistryTest(unittest.TestCase):
    def test_high_risk_models_match_models_md(self):
        from core.config.paths import ROOT_DIR

        text = (ROOT_DIR / "docs" / "MODELS.md").read_text(encoding="utf-8")
        for code in V.HIGH_RISK:
            self.assertIn(f"| {code} |", text)
            row = next(line for line in text.splitlines() if line.startswith(f"| {code} |"))
            self.assertIn("YÜKSEK", row)


class CheckTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def report(self, code, day, verdict="kullanılabilir"):
        (self.dir / f"{code}.md").write_text(f"# {code}\nTarih: {day}\nKarar: {verdict}\n", encoding="utf-8")

    def test_none_yet_is_information(self):
        state, text = V.status(date(2026, 10, 30), self.dir)
        self.assertEqual(state, "info")
        self.assertIn(f"0/{len(V.HIGH_RISK)}", text)

    def test_counts_verdicts_and_expiry(self):
        self.report("M15", "2026-10-29", "kısıtlı kullanılabilir")
        self.report("M14", "2025-09-01")
        state, text = V.status(date(2026, 10, 30), self.dir)
        self.assertEqual(state, "warn")  # M14 is older than a year
        self.assertIn("2/", text)
        self.assertIn("süresi geçen: M14", text)
        self.assertIn("M15 kısıtlı kullanılabilir", text)
        reports = V.reports(self.dir)
        self.assertEqual(reports["M15"].verdict, "kısıtlı kullanılabilir")

    def test_unusable_is_a_warning(self):
        self.report("M15", "2026-10-29", "kullanılamaz")
        self.assertEqual(V.status(date(2026, 10, 30), self.dir)[0], "warn")

    def test_health_line(self):
        from core.reports import health

        names = [c.name for c in health.health_checks(online=False)]
        self.assertIn("Model doğrulama", names)


if __name__ == "__main__":
    unittest.main()
