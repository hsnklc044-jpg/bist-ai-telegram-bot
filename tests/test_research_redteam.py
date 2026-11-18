"""Red-team findings on core/research (18.11.2026 night, clean-context review). Each test reproduces one
finding and failed before its fix."""

import math
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from core.research import costs, cpcv, multiple
from core.research import experiments as ex


class CpcvAfterSidePurgeTest(unittest.TestCase):  # finding 1 (YÜKSEK)
    def test_training_points_right_after_a_test_group_are_purged(self):
        splits = cpcv.splits(600, n_groups=6, k_test=2, horizon=5, embargo=0)
        train, _ = next((tr, te) for tr, te in splits if te[0] == 100 and 300 in te)
        for t in (200, 201, 202, 203, 204, 400, 404):
            self.assertNotIn(t, train)
        self.assertIn(205, train)
        self.assertIn(405, train)

    def test_the_leak_check_sees_the_after_side(self):
        test = np.arange(100, 200)
        train = np.concatenate([np.arange(0, 95), np.arange(200, 600)])  # before purged, after not
        self.assertEqual(cpcv.leaks(train, test, horizon=5), [200, 201, 202, 203, 204])


class CpcvShortDataTest(unittest.TestCase):  # finding 2 (YÜKSEK)
    def test_empty_training_sets_give_none_not_a_number(self):
        df = pd.DataFrame(np.random.default_rng(0).normal(size=(20, 3)))
        df[0] += 5
        self.assertIsNone(cpcv.pbo(df, n_groups=10, k_test=8, horizon=5, embargo=5))

    def test_single_row_groups_give_none(self):
        df = pd.DataFrame(np.random.default_rng(1).normal(size=(16, 3)))
        self.assertIsNone(cpcv.pbo(df, n_groups=16, k_test=15, horizon=0, embargo=0))


class ExperimentTamperTest(unittest.TestCase):  # findings 3, 4, 5
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "deneyler"
        ex.register("a", {"s": 1}, "c", "d", {}, root=self.root)
        ex.record_result("a", {"x": 1}, root=self.root)
        ex.record_result("a", {"x": 2}, root=self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def test_deleting_the_manifest_is_caught(self):
        (self.root / ex.MANIFEST).unlink()
        self.assertTrue(ex.verify(root=self.root))

    def test_editing_a_file_and_its_manifest_line_is_caught(self):
        p = self.root / "a" / "sonuc_0001.json"
        p.write_text("{}", encoding="utf-8")
        m = self.root / ex.MANIFEST
        lines = m.read_text(encoding="utf-8").splitlines()
        lines = [ln.replace(ln.split(",")[1], ex._sha(p)) if "sonuc_0001" in ln else ln for ln in lines]
        m.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.assertTrue(ex.verify(root=self.root))

    def test_dropping_the_last_run_everywhere_is_caught_by_the_outside_head(self):
        head = ex.head(root=self.root)
        (self.root / "a" / "sonuc_0002.json").unlink()
        for name in (ex.MANIFEST, ex.COUNTER):
            f = self.root / name
            f.write_text("\n".join(f.read_text(encoding="utf-8").splitlines()[:-1]) + "\n", encoding="utf-8")
        self.assertTrue(ex.verify(root=self.root, expected_head=head))

    def test_a_stray_file_is_caught(self):
        (self.root / "a" / "sonuc_0005.json").write_text("{}", encoding="utf-8")
        self.assertTrue(any("kayıtsız" in p for p in ex.verify(root=self.root)))

    def test_counter_rows_moved_between_experiments_are_caught(self):
        ex.register("b", {"s": 1}, "c", "d", {}, root=self.root)
        c = self.root / ex.COUNTER
        c.write_text(c.read_text(encoding="utf-8").replace(",a,2", ",b,1"), encoding="utf-8")
        self.assertTrue(ex.verify(root=self.root))

    def test_names_are_lowercase_and_not_windows_devices(self):
        for bad in ("ABC", "Abc", "con", "COM1.json", "aux.x", "nul", "lpt9"):
            with self.assertRaises(ValueError, msg=bad):
                ex.register(bad, {}, "c", "d", {}, root=self.root)

    def test_a_failed_write_leaves_nothing_behind(self):
        with self.assertRaises((TypeError, ValueError)):
            ex.record_result("a", {"x": object()}, root=self.root)
        self.assertFalse((self.root / "a" / "sonuc_0003.json").exists())
        self.assertEqual(ex.record_result("a", {"x": 3}, root=self.root), 3)
        with self.assertRaises(ValueError):
            ex.record_result("a", {"x": math.nan}, root=self.root)
        self.assertEqual(ex.verify(root=self.root), [])


class CostEdgeTest(unittest.TestCase):  # findings 6, 7
    T = [(0.0, 0.01), (20.0, 0.02)]

    def test_float_noise_does_not_move_a_whole_tick(self):
        self.assertAlmostEqual(costs.round_to_tick(0.1 + 0.2, self.T, side="buy"), 0.30)
        self.assertAlmostEqual(costs.round_to_tick(0.7 - 0.4, self.T, side="sell"), 0.30)

    def test_non_finite_and_unknown_inputs_are_refused(self):
        with self.assertRaises(ValueError):
            costs.round_to_tick(math.inf, self.T)
        with self.assertRaises(ValueError):
            costs.round_to_tick(1.0, [(0.0, math.nan)])
        with self.assertRaises(ValueError):
            costs.round_to_tick(1.0, self.T, side="BUY")
        with self.assertRaises(ValueError):
            costs.slippage(order_tl=1, adv_tl=math.inf, base=0, impact=0.1)
        with self.assertRaises(ValueError):
            costs.within_capacity(order_tl=math.inf, adv_tl=math.inf, max_share=0.1)

    def test_band_bounds_must_sit_on_their_tick_grid(self):
        with self.assertRaises(ValueError):
            costs.round_to_tick(2.549, [(0.0, 0.01), (2.5, 0.03)])


class MultipleConsistencyTest(unittest.TestCase):  # finding 8
    def test_both_rules_reject_at_the_boundary(self):
        self.assertEqual(multiple.bonferroni_reject([0.01] * 5, 0.05), [True] * 5)

    def test_non_numeric_input_is_refused(self):
        for bad in ([True, 0.2], ["0.2"], [None]):
            with self.assertRaises(ValueError, msg=bad):
                multiple.bh_adjust(bad)


if __name__ == "__main__":
    unittest.main()
