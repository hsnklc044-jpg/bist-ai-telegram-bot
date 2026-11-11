"""The a5 pre-registration (K-89, 11.11.2026): written before any data, frozen. This test keeps its fields in place."""

import unittest
from pathlib import Path


def section() -> str:
    log = Path("docs/RESEARCH_LOG.md").read_text(encoding="utf-8")
    start = log.index("## a5 ön kaydı — H6a, H6b, H7a, H7b")
    return log[start:log.index("\n## ", start + 5)]


class A5Test(unittest.TestCase):
    def test_the_four_hypotheses_with_their_fixed_rules(self):
        text = section()
        for part in ("| H6a | Değer + kalite |", "PD/DD'si en düşük %30", "Piotroski F ≥ 7",
                     "| H6b | Değer + kalite + trend |", "200 günlük ortalama",
                     "| H7a | Betik karnesi |", "≥ 70", "< 50", "en fazla 10 pozisyon", "| H7b | Profesyonel puan |"):
            self.assertIn(part, text)

    def test_the_decision_rule_the_date_gate_and_the_rejections(self):
        text = section()
        self.assertIn("%98,75 GA", text)  # Bonferroni for 4 hypotheses
        self.assertIn("27.10.2027'den önce çalıştırılmaz", text)
        self.assertIn("holdout kodla kapalı", text)
        self.assertIn("Seviye 1 ya da 2", text)
        self.assertIn("### Reddedilen", text)
        self.assertIn("### Beklenti (ölçümden önce)", text)

    def test_the_program_table_and_the_decision_point_to_it(self):
        self.assertIn("| a5 | ön kayıt 11.11.2026", Path("docs/RESEARCH_PROGRAM.md").read_text(encoding="utf-8"))
        self.assertIn("**K-89. a5 ön kaydı", Path("docs/DECISIONS.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()


class R1Test(unittest.TestCase):
    """K-91: the r1 replication was pre-registered before any measurement."""

    def test_the_period_the_data_and_the_rules(self):
        log = Path("docs/RESEARCH_LOG.md").read_text(encoding="utf-8")
        start = log.index("## r1 ön kaydı")
        text = log[start:log.index("\n## ", start + 5)]
        for part in ("2016-01-04 – 2023-07-31", "holdout", "XU100'ün o günkü getirisi", "deneme bütçesinden harcamaz",
                     "### Reddedilen", "### Beklenti"):
            self.assertIn(part, text)
