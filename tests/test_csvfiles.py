"""Ö67: core/infrastructure/csvfiles.py had no test of its own (ROADMAP öz-denetim 11)."""

import tempfile
import unittest
from pathlib import Path

from core.infrastructure.csvfiles import open_append, read_rows
from core.infrastructure.exceptions import PersonalFileError


class ReadRowsTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.path = self.dir / "kayit.csv"

    def write(self, data: bytes):
        self.path.write_bytes(data)

    def test_missing_file_is_empty(self):
        self.assertEqual(read_rows(self.path), [])

    def test_rows_with_line_numbers_and_bom(self):
        self.write("﻿a,b\n1,2\n3,4\n".encode())
        self.assertEqual(read_rows(self.path, required=("a", "b")), [(2, {"a": "1", "b": "2"}), (3, {"a": "3", "b": "4"})])

    def test_zero_bytes_is_an_error(self):
        self.write(b"")
        with self.assertRaises(PersonalFileError) as cm:
            read_rows(self.path)
        self.assertIn("0 bayt", str(cm.exception))

    def test_missing_column_names_line_1(self):
        self.write(b"a\n1\n")
        with self.assertRaises(PersonalFileError) as cm:
            read_rows(self.path, required=("a", "b"))
        self.assertEqual(cm.exception.line, 1)
        self.assertIn("'b'", cm.exception.reason)

    def test_cut_row_and_extra_field_name_their_line(self):
        self.write(b"a,b\n1,2\n3\n")
        with self.assertRaises(PersonalFileError) as cm:
            read_rows(self.path)
        self.assertEqual((cm.exception.line, cm.exception.reason), (3, "satır yarım kalmış (alan eksik)"))
        self.write(b"a,b\n1,2,3\n")
        with self.assertRaises(PersonalFileError) as cm:
            read_rows(self.path)
        self.assertEqual((cm.exception.line, cm.exception.reason), (2, "başlıktan fazla alan var"))

    def test_nul_bytes_and_bad_encoding(self):
        self.write(b"a,b\n1,\x002\n")
        with self.assertRaises(PersonalFileError) as cm:
            read_rows(self.path)
        self.assertIn("okunamayan", cm.exception.reason)
        self.write(b"a,b\n\xff\xfe,1\n")
        with self.assertRaises(PersonalFileError) as cm:
            read_rows(self.path)
        self.assertIn("okunamıyor", cm.exception.reason)

    def test_the_file_is_never_changed(self):
        data = b"a,b\n1\n"
        self.write(data)
        with self.assertRaises(PersonalFileError):
            read_rows(self.path)
        self.assertEqual(self.path.read_bytes(), data)


class OpenAppendTest(unittest.TestCase):
    def setUp(self):
        self.path = Path(tempfile.mkdtemp()) / "alt" / "kayit.csv"

    def append(self, text):
        fh, new = open_append(self.path)
        with fh:
            fh.write(text)
        return new

    def test_new_file_and_folder(self):
        self.assertTrue(self.append("a,b\n"))
        self.assertFalse(self.append("1,2\n"))
        self.assertEqual(self.path.read_bytes(), b"a,b\n1,2\n")

    def test_cut_last_line_gets_a_newline_first(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_bytes(b"a,b\n1,")  # power loss mid-row
        self.append("3,4\n")
        self.assertEqual(self.path.read_bytes(), b"a,b\n1,\n3,4\n")

    def test_empty_file_gets_no_extra_newline(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_bytes(b"")
        self.assertFalse(self.append("a,b\n"))
        self.assertEqual(self.path.read_bytes(), b"a,b\n")


if __name__ == "__main__":
    unittest.main()
