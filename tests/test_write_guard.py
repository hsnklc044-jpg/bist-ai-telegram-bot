"""
The guard behind "tests never write to the real data/ or logs/ folders".

tests/conftest.py takes a snapshot of both folders when the test session
starts and fails the session if anything was created, changed or
deleted. These tests check the guard itself on a temporary folder.
"""

import os
import tempfile
import unittest
from pathlib import Path

from tests.write_guard import changes, snapshot


class WriteGuardTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / "ledger.csv").write_text("id,date\n", encoding="utf-8")
        (self.root / "sub").mkdir()
        (self.root / "sub" / "old.txt").write_text("x", encoding="utf-8")
        self.before = snapshot([self.root])

    def test_nothing_changed(self):
        self.assertEqual(changes(self.before, snapshot([self.root])), [])

    def test_created_file_is_caught(self):
        (self.root / "new.json").write_text("{}", encoding="utf-8")
        self.assertEqual(changes(self.before, snapshot([self.root])), [f"oluşturuldu: {self.root / 'new.json'}"])

    def test_changed_file_is_caught_even_with_the_same_size_and_time(self):
        path = self.root / "ledger.csv"
        stat = path.stat()
        path.write_text("id,DATE\n", encoding="utf-8")  # same size
        os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))  # same time
        self.assertEqual(changes(self.before, snapshot([self.root])), [f"değişti: {path}"])

    def test_appended_file_is_caught(self):
        with open(self.root / "ledger.csv", "a", encoding="utf-8") as fh:
            fh.write("1,2026-10-27\n")
        self.assertEqual(changes(self.before, snapshot([self.root])), [f"değişti: {self.root / 'ledger.csv'}"])

    def test_deleted_file_is_caught(self):
        (self.root / "sub" / "old.txt").unlink()
        self.assertEqual(changes(self.before, snapshot([self.root])), [f"silindi: {self.root / 'sub' / 'old.txt'}"])

    def test_missing_folder_is_fine(self):
        self.assertEqual(snapshot([self.root / "yok"]), {})


class LiveFilesTest(unittest.TestCase):
    def test_files_of_the_running_bot_count_only_on_ci(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "heartbeat.txt").write_text("1", encoding="utf-8")
            (root / "ledger.csv").write_text("x", encoding="utf-8")
            self.assertEqual(set(snapshot([root], strict=False)), {str(root / "ledger.csv")})
            self.assertEqual(len(snapshot([root], strict=True)), 2)
