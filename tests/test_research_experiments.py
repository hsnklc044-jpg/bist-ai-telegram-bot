"""QB-ARS-1 §6 and S-1: the experiment registry and the trial counter (Faz A, 18.11.2026).

Records are append-only (ANAYASA Md. 11): an experiment folder is written once, results never overwrite,
the trial counter only grows and cannot be reset, and an integrity check reports any changed or missing
file (KT-03 covers this folder).
"""

import json
import tempfile
import unittest
from pathlib import Path

from core.research import experiments as ex


class RegistryTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "deneyler"

    def tearDown(self):
        self._tmp.cleanup()

    def _register(self, name="a4-ornek"):
        return ex.register(name, preregistration={"soru": "deneme", "esik": "ön kayıtta"},
                           code_version="abc1234", data_digest="sha256:00", params={"n": 20}, root=self.root)

    def test_register_writes_one_folder_with_the_record(self):
        folder = self._register()
        record = json.loads((folder / "kayit.json").read_text(encoding="utf-8"))
        self.assertEqual(record["deney"], "a4-ornek")
        self.assertEqual(record["kod_surumu"], "abc1234")
        self.assertEqual(record["veri_ozeti"], "sha256:00")
        self.assertIn("kayit_zamani", record)

    def test_the_same_experiment_cannot_be_registered_twice(self):
        self._register()
        with self.assertRaises(ex.RecordExistsError):
            self._register()

    def test_bad_names_are_refused(self):
        for name in ("", "../kacis", "a/b", "a\\b", "."):
            with self.assertRaises(ValueError, msg=name):
                self._register(name)

    def test_results_get_the_next_trial_number_and_never_overwrite(self):
        self._register()
        n1 = ex.record_result("a4-ornek", {"sharpe": 0.1}, root=self.root)
        n2 = ex.record_result("a4-ornek", {"sharpe": 0.2}, root=self.root)
        self.assertEqual((n1, n2), (1, 2))
        self.assertEqual(ex.trial_count(root=self.root), 2)
        self.assertEqual(ex.trial_count("a4-ornek", root=self.root), 2)
        first = json.loads((self.root / "a4-ornek" / "sonuc_0001.json").read_text(encoding="utf-8"))
        self.assertEqual(first["sonuc"], {"sharpe": 0.1})

    def test_a_result_needs_a_registered_experiment(self):
        with self.assertRaises(FileNotFoundError):
            ex.record_result("kayitsiz", {"x": 1}, root=self.root)

    def test_the_counter_has_no_reset(self):
        self.assertFalse(any("reset" in n or "sifirla" in n for n in dir(ex)))

    def test_integrity_is_clean_after_normal_use(self):
        self._register()
        ex.record_result("a4-ornek", {"x": 1}, root=self.root)
        self.assertEqual(ex.verify(root=self.root), [])

    def test_integrity_reports_a_changed_record(self):  # canary for KT-03
        folder = self._register()
        (folder / "kayit.json").write_text("{}", encoding="utf-8")
        problems = ex.verify(root=self.root)
        self.assertTrue(any("değişti" in p and "kayit.json" in p for p in problems), problems)

    def test_integrity_reports_a_deleted_result(self):  # canary for KT-03
        self._register()
        ex.record_result("a4-ornek", {"x": 1}, root=self.root)
        (self.root / "a4-ornek" / "sonuc_0001.json").unlink()
        problems = ex.verify(root=self.root)
        self.assertTrue(any("eksik" in p and "sonuc_0001.json" in p for p in problems), problems)

    def test_integrity_reports_a_shrunk_counter(self):  # canary: the counter cannot be reset
        self._register()
        ex.record_result("a4-ornek", {"x": 1}, root=self.root)
        ex.record_result("a4-ornek", {"x": 2}, root=self.root)
        counter = self.root / ex.COUNTER
        lines = counter.read_text(encoding="utf-8").splitlines()
        counter.write_text("\n".join(lines[:2]) + "\n", encoding="utf-8")
        problems = ex.verify(root=self.root)
        self.assertTrue(any(ex.COUNTER in p for p in problems), problems)

    def test_an_empty_root_is_clean(self):
        self.assertEqual(ex.verify(root=self.root), [])
        self.assertEqual(ex.trial_count(root=self.root), 0)

    def test_summary_line_for_the_monthly_report(self):
        self._register()
        ex.record_result("a4-ornek", {"x": 1}, root=self.root)
        self.assertEqual(ex.summary_line(root=self.root), "Bu ay 1 deneme, 1 deney kayıtlı.")


if __name__ == "__main__":
    unittest.main()
