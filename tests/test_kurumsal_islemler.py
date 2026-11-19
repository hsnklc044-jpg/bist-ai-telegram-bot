"""#1 (K-113 Dalga 2): corporate-actions event table, schema and validator only.

Every row here is made up (symbols TEST1..); the tracked table holds only the header.
"""

import csv
import tempfile
import unittest
from pathlib import Path

from core.market import kurumsal_islemler as ki

ROOT = Path(__file__).resolve().parents[1]


def row(**values) -> dict:
    base = {c: "" for c in ki.COLUMNS}
    base.update(symbol="TEST1", event_type="bedelsiz", ex_date="2026-01-05", ratio="1",
                source_url="https://ornek.invalid/duyuru")
    base.update(values)
    return base


class RowTest(unittest.TestCase):
    def test_valid_rows_of_every_type_pass(self):
        rows = [
            row(),
            row(symbol="TEST2.IS", event_type="bolunme", ratio="4"),
            row(event_type="bedelli", ratio="0.5", amount="1", ex_date="2026-02-02"),
            row(event_type="temettu", ratio="", amount="2.35", ex_date="2026-03-03"),
            row(event_type="kod_degisikligi", ratio="", new_symbol="TEST9", ex_date="2026-04-01"),
            row(event_type="birlesme", ratio="", new_symbol="TEST8", ex_date="2026-05-04"),
        ]
        self.assertEqual(ki.validate_rows(rows), [])

    def test_unknown_event_type_is_refused(self):
        problems = ki.validate_rows([row(event_type="split")])
        self.assertEqual(len(problems), 1)
        self.assertIn("event_type", problems[0])

    def test_bad_dates_are_refused(self):
        for value in ("", "05.01.2026", "2026-02-30", "2026-1-5"):
            problems = ki.validate_rows([row(ex_date=value)])
            self.assertTrue(problems, value)
            self.assertIn("ex_date", problems[0])

    def test_source_is_required(self):
        self.assertIn("source_url", ki.validate_rows([row(source_url="")])[0])
        self.assertIn("source_url", ki.validate_rows([row(source_url="ornek.com/x")])[0])

    def test_numbers_must_fit_the_event_type(self):
        self.assertTrue(ki.validate_rows([row(ratio="")]))  # bedelsiz needs a ratio
        self.assertTrue(ki.validate_rows([row(ratio="-1")]))
        self.assertTrue(ki.validate_rows([row(ratio="abc")]))
        self.assertTrue(ki.validate_rows([row(ratio="nan")]))
        self.assertTrue(ki.validate_rows([row(event_type="bedelli", ratio="1")]))  # no price
        self.assertTrue(ki.validate_rows([row(event_type="temettu", ratio="", amount="0")]))
        self.assertTrue(ki.validate_rows([row(event_type="kod_degisikligi", ratio="")]))
        self.assertTrue(ki.validate_rows([row(event_type="kod_degisikligi", ratio="", new_symbol="TEST1")]))

    def test_bad_symbol_and_duplicates_are_refused(self):
        self.assertIn("symbol", ki.validate_rows([row(symbol="test 1")])[0])
        problems = ki.validate_rows([row(), row(note="tekrar")])
        self.assertEqual(len(problems), 1)
        self.assertIn("tekrar", problems[0])

    def test_problem_names_the_line(self):
        problems = ki.validate_rows([row(), row(event_type="x", ex_date="2026-01-06")])
        self.assertTrue(problems[0].startswith("satır 3"))


class FileTest(unittest.TestCase):
    def _write(self, header, rows) -> Path:
        path = Path(tempfile.mkdtemp()) / "k.csv"
        with open(path, "w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(header)
            for r in rows:
                writer.writerow([r[c] for c in header])
        return path

    def test_file_with_the_schema_header_passes(self):
        self.assertEqual(ki.validate_file(self._write(ki.COLUMNS, [row()])), [])

    def test_wrong_header_is_refused(self):
        header = [c for c in ki.COLUMNS if c != "source_url"]
        problems = ki.validate_file(self._write(header, [row()]))
        self.assertTrue(problems)
        self.assertIn("başlık", problems[0])

    def test_missing_file_is_reported(self):
        self.assertIn("bulunamadı", ki.validate_file(Path(tempfile.mkdtemp()) / "yok.csv")[0])

    def test_tracked_table_is_header_only(self):
        path = ROOT / "data" / "kurumsal_islemler.csv"
        self.assertEqual(ki.validate_file(path), [])
        with open(path, encoding="utf-8", newline="") as fh:
            lines = [r for r in csv.reader(fh) if r]
        self.assertEqual(lines, [list(ki.COLUMNS)])


if __name__ == "__main__":
    unittest.main()
