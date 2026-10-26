"""
The engine must reproduce the saved golden results exactly
(up to floating point noise across machines).
"""

import json
import math
import unittest

from tests.golden import RESULTS_FILE, scenarios

REL_TOL = 1e-9


class GoldenResultsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.expected = json.loads(RESULTS_FILE.read_text(encoding="utf-8"))
        cls.actual = json.loads(json.dumps(scenarios()))

    def assert_same(self, expected, actual, path):
        if isinstance(expected, dict):
            self.assertEqual(sorted(expected), sorted(actual), path)
            for key in expected:
                self.assert_same(expected[key], actual[key], f"{path}.{key}")
        elif isinstance(expected, list):
            self.assertEqual(len(expected), len(actual), f"{path}: length")
            for i, (e, a) in enumerate(zip(expected, actual, strict=True)):
                self.assert_same(e, a, f"{path}[{i}]")
        elif isinstance(expected, float) and isinstance(actual, (int, float)):
            self.assertTrue(
                math.isclose(expected, actual, rel_tol=REL_TOL, abs_tol=1e-9),
                f"{path}: expected {expected!r}, got {actual!r}",
            )
        else:
            self.assertEqual(expected, actual, path)

    def test_scenarios_match_golden(self):
        self.assertEqual(sorted(self.expected), sorted(self.actual))
        for name in self.expected:
            with self.subTest(scenario=name):
                self.assert_same(self.expected[name], self.actual[name], name)

    def test_scenarios_trade(self):
        # guard against a golden file that silently tests nothing
        for name, summary in self.expected.items():
            if "trades" in summary:
                with self.subTest(scenario=name):
                    self.assertGreaterEqual(len(summary["trades"]), 2)

    def test_special_days_are_exercised(self):
        on = {t[0]: t for t in self.expected["special_days_locks_on"]["trades"]}
        off = {t[0]: t for t in self.expected["special_days_locks_off"]["trades"]}

        # S05: the entry day is locked at the upper limit -> no purchase
        self.assertNotIn("S05", on)
        self.assertIn("S05", off)
        # S03: the exit waits through two locked limit-down days
        self.assertEqual(off["S03"][3], "2026-05-11")
        self.assertEqual(on["S03"][3], "2026-05-13")
        # S07: a gap below the stop fills at the (lower) open, not at the stop
        self.assertEqual(on["S07"][5], "stop")
        self.assertEqual(on["S07"][3], "2026-06-22")


if __name__ == "__main__":
    unittest.main()
