"""QB-ARS-1 S-2: multiple-testing corrections (Faz B, 18.11.2026).

Known example: Benjamini and Hochberg (1995), the 15 p-values of the thrombolysis trial family, as
reproduced in the SciPy manual for scipy.stats.false_discovery_control (read 18.11.2026,
https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.false_discovery_control.html).
Published there: Bonferroni rejects the first 3 at 5%; the BH-adjusted p-values start
0.0015, 0.003, 0.0095, 0.035625, 0.0603, 0.06385714, 0.06385714, 0.0645, 0.0765, 0.486, 0.58118182, 0.714875.
"""

import unittest

from core.research import multiple

PS = [0.0001, 0.0004, 0.0019, 0.0095, 0.0201, 0.0278, 0.0298, 0.0344,
      0.0459, 0.3240, 0.4262, 0.5719, 0.6528, 0.7590, 1.000]
BH_PUBLISHED = [0.0015, 0.003, 0.0095, 0.035625, 0.0603, 0.06385714, 0.06385714, 0.0645, 0.0765, 0.486,
                0.58118182, 0.714875]


class BonferroniTest(unittest.TestCase):
    def test_published_example_rejects_the_first_three(self):
        self.assertEqual(multiple.bonferroni_reject(PS, 0.05), [True] * 3 + [False] * 12)

    def test_adjusted_values_are_capped_at_one(self):
        adjusted = multiple.bonferroni_adjust(PS)
        self.assertAlmostEqual(adjusted[0], 0.0015, places=10)
        self.assertEqual(max(adjusted), 1.0)


class BenjaminiHochbergTest(unittest.TestCase):
    def test_published_adjusted_values(self):
        adjusted = multiple.bh_adjust(PS)
        for got, want in zip(adjusted, BH_PUBLISHED, strict=False):
            self.assertAlmostEqual(got, want, places=6)

    def test_published_example_rejects_the_first_four_at_five_percent(self):
        self.assertEqual(multiple.bh_reject(PS, 0.05), [True] * 4 + [False] * 11)

    def test_order_of_input_is_kept(self):
        shuffled = [PS[3], PS[0], PS[14], PS[1]]
        adjusted = multiple.bh_adjust(shuffled)
        self.assertEqual(adjusted, [multiple.bh_adjust(sorted(shuffled))[2],
                                    multiple.bh_adjust(sorted(shuffled))[0],
                                    multiple.bh_adjust(sorted(shuffled))[3],
                                    multiple.bh_adjust(sorted(shuffled))[1]])

    def test_bad_input_is_refused(self):
        for bad in ([], [0.1, 1.2], [-0.1], [float("nan")]):
            with self.assertRaises(ValueError, msg=bad):
                multiple.bh_adjust(bad)
        with self.assertRaises(ValueError):
            multiple.bh_reject(PS, 0)


if __name__ == "__main__":
    unittest.main()
