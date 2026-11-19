"""#13: decision journal (docs/KARAR_DEFTERI.csv), append-only, and the N counter per hypothesis card."""

import csv
import shutil
import tempfile
import unittest
from pathlib import Path

from core.research import experiments
from core.research import karar_defteri as kd


def entry(**kw):
    base = dict(tarih="2026-11-20", karar_no="K-113", tur="esik_onayi", kart="T1", ozet="Eşik onaylandı.",
                beklenti="b", en_kotu_senaryo="e", gerekce="g", n_etkisi="1", sayaci_sifirlar="hayir")
    base.update(kw)
    return base


class JournalTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.path = self.dir / "KARAR_DEFTERI.csv"
        shutil.copy(kd.JOURNAL, self.path)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_project_journal_seeded_and_valid(self):
        rows = kd.read(kd.JOURNAL)
        self.assertEqual([r["karar_no"] for r in rows], ["K-110", "K-111", "K-112"])
        self.assertEqual({r["n_etkisi"] for r in rows}, {"0"})
        with open(kd.JOURNAL, encoding="utf-8", newline="") as f:
            self.assertEqual(tuple(next(csv.reader(f))), kd.COLUMNS)

    def test_bad_rows_refused(self):
        for bad in (entry(tur="baska"), entry(karar_no="113"), entry(n_etkisi="2"), entry(sayaci_sifirlar="belki"),
                    entry(tarih="20.11.2026"), entry(ozet=""),
                    entry(tur="hata_duzeltmesi", sayaci_sifirlar="evet"),
                    entry(tur="kural_duzeltmesi", sayaci_sifirlar="hayir")):
            with self.assertRaises(ValueError, msg=str(bad)):
                kd.check(bad)
        kd.check(entry(tur="hata_duzeltmesi", sayaci_sifirlar="hayir"))
        kd.check(entry(tur="kural_duzeltmesi", sayaci_sifirlar="evet"))

    def test_append_adds_at_end_only(self):
        before = self.path.read_text(encoding="utf-8")
        kd.append(entry(), self.path)
        after = self.path.read_text(encoding="utf-8")
        self.assertTrue(after.startswith(before))
        self.assertEqual(kd.read(self.path)[-1]["karar_no"], "K-113")
        with self.assertRaises(ValueError):
            kd.append(entry(tur="yok"), self.path)
        self.assertEqual(len(kd.read(self.path)), 4)

    def test_edited_or_reordered_old_row_detected(self):
        base = self.path.read_text(encoding="utf-8")
        self.assertEqual(kd.verify(self.path, base), [])
        kd.append(entry(), self.path)
        self.assertEqual(kd.verify(self.path, base), [])  # appending is fine
        rows = kd.read(self.path)
        edited = [dict(rows[0], ozet="Sonradan değiştirildi."), *rows[1:]]
        kd._write_rows(edited, self.path)
        problems = kd.verify(self.path, base)
        self.assertTrue(problems)
        self.assertIn("K-110", problems[0])
        kd._write_rows([rows[1], rows[0], *rows[2:]], self.path)
        self.assertTrue(kd.verify(self.path, base))
        kd._write_rows(rows[1:], self.path)  # a deleted row
        self.assertTrue(kd.verify(self.path, base))

    def test_project_journal_matches_git_head(self):
        base = kd.committed_text()
        if base is None:
            self.skipTest("git ya da HEAD'de dosya yok")
        self.assertEqual(kd.verify(kd.JOURNAL, base), [])


class CounterTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.path = self.dir / "KARAR_DEFTERI.csv"
        shutil.copy(kd.JOURNAL, self.path)
        self.root = self.dir / "deneyler"

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_n_by_card_sums_journal_and_trial_counter(self):
        kd.append(entry(kart="T1"), self.path)
        kd.append(entry(kart="T1", n_etkisi="0", tur="diger"), self.path)
        kd.append(entry(kart="F2"), self.path)
        self.assertEqual(kd.n_by_card(self.path, self.root), {"T1": 1, "F2": 1})
        self.root.mkdir()
        with open(self.root / experiments.COUNTER, "w", encoding="utf-8", newline="") as f:
            f.write("zaman,deney,n\n2026-11-20T10:00,t1,1\n2026-11-20T11:00,t1,2\n2026-11-20T12:00,baska,1\n")
        self.assertEqual(kd.n_by_card(self.path, self.root), {"T1": 3, "F2": 1})


if __name__ == "__main__":
    unittest.main()
