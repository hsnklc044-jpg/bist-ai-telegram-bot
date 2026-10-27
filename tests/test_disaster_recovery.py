"""CHARTER E1: the 'PC is gone' steps in docs/DISASTER_RECOVERY.md must work as written."""

import importlib.util
import re
import tempfile
import unittest
from pathlib import Path

from core import backup
from core.ledger import load_ledger

ROOT = Path(__file__).resolve().parents[1]
DOC = (ROOT / "docs" / "DISASTER_RECOVERY.md").read_text(encoding="utf-8")


class DocumentedStepsTest(unittest.TestCase):
    def test_every_script_exists(self):
        scripts = set(re.findall(r"scripts\\(\w+\.ps1)", DOC))
        self.assertTrue(scripts)
        for name in scripts:
            self.assertTrue((ROOT / "scripts" / name).exists(), name)

    def test_every_python_module_exists(self):
        modules = set(re.findall(r"python -m ([\w.]+)", DOC))
        self.assertTrue(modules)
        for module in modules:
            self.assertIsNotNone(importlib.util.find_spec(module), module)

    def test_every_env_name_is_one_the_code_reads(self):
        names = set(re.findall(r"^\s*([A-Z_]{4,})=", DOC, re.M))
        self.assertTrue(names)
        code = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "core").rglob("*.py"))
        for name in names:
            self.assertTrue(f'"{name}"' in code, f"{name} is not read anywhere in core/")



class HandbookLinksTest(unittest.TestCase):
    """CHARTER J1: the handbook only points at documents that exist."""

    def test_every_referenced_document_exists(self):
        text = (ROOT / "docs" / "HANDBOOK.md").read_text(encoding="utf-8")
        refs = set(re.findall(r"\b((?:docs/)?[A-Z_]+\.md)\b", text))
        self.assertTrue(refs)
        for ref in refs:
            path = ROOT / ref if ref.startswith("docs/") or ref == "CHANGELOG.md" else ROOT / "docs" / ref
            self.assertTrue(path.exists(), ref)


class FreshMachineRestoreTest(unittest.TestCase):
    def test_restore_into_an_empty_data_folder(self):
        ledger = "id,date,account,symbol,side,quantity,price,fee,note\n1,2026-10-01,real,THYAO.IS,buy,10,100,1,\n"
        with tempfile.TemporaryDirectory() as tmp:
            old, new, target = Path(tmp) / "old", Path(tmp) / "new", Path(tmp) / "yedek"
            old.mkdir()
            new.mkdir()
            (old / "ledger.csv").write_text(ledger, encoding="utf-8")
            (old / "watchlist.json").write_text('{"1": ["EREGL.IS"]}', encoding="utf-8")
            made = backup.create_backup([old / "ledger.csv", old / "watchlist.json"], target=target)
            restored, safety = backup.restore_backup(made.path, data_dir=new)
            self.assertIsNone(safety)  # nothing to protect on a new machine
            self.assertEqual((new / "ledger.csv").read_text(encoding="utf-8"), ledger)
            self.assertEqual(len(load_ledger(new / "ledger.csv")), 1)
            self.assertIn("watchlist.json", " ".join(restored))


if __name__ == "__main__":
    unittest.main()
