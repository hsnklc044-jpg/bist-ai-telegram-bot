"""Two wording faults in the 05.11.2026 report: "23.10.2026'den" (should be 'dan) and the support line
"güç 0 ölçülmemiş puan, -0,0 ATR" (a contradictory phrase and a negative zero)."""

import unittest
from datetime import date

from core.analytics import levels as L
from core.reports.daily import date_from


class DateSuffixTest(unittest.TestCase):
    def test_suffix_follows_the_spoken_year(self):
        cases = {2026: "'dan", 2025: "'ten", 2024: "'ten", 2023: "'ten", 2022: "'den", 2021: "'den",
                 2027: "'den", 2028: "'den", 2029: "'dan", 2030: "'dan", 2040: "'tan", 2050: "'den",
                 2060: "'tan", 2070: "'ten", 2080: "'den", 2090: "'dan", 2020: "'den", 2000: "'den",
                 2100: "'den"}
        for year, suffix in cases.items():
            self.assertEqual(date_from(date(year, 10, 23)), f"23.10.{year}{suffix}", year)


class AtrTextTest(unittest.TestCase):
    def test_no_negative_zero(self):
        self.assertEqual(L.atr_text(-0.04), "0,0")
        self.assertEqual(L.atr_text(0.04), "0,0")
        self.assertEqual(L.atr_text(-1.26), "-1,3")
        self.assertEqual(L.atr_text(0.5), "+0,5")

    def test_position_line_reads_cleanly(self):
        from tests.test_levels import market

        line = L.position_line(market())
        self.assertIn("güç puanı", line)
        self.assertNotIn("ölçülmemiş puan,", line)
        self.assertNotIn("-0,0", line)
        self.assertIn("kapanışa uzaklık", line)


if __name__ == "__main__":
    unittest.main()
