"""Ö71 (18.11.2026): scripts/bildir.py must use the code next to it, not the old install folder.

The live install moved from C:\\Projeler\\QuantBIST to C:\\Projeler\\QuantBIST-yeni on 03.11.2026; bildir.py
kept the old path, so the updater's Telegram notices ran the old code (and would fail once that folder
is gone).
"""

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "bildir.py"


class BildirPathTest(unittest.TestCase):
    def test_project_is_the_folder_the_script_is_in(self):
        spec = importlib.util.spec_from_file_location("bildir_under_test", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(Path(module.PROJECT).resolve(), ROOT)

    def test_no_hard_coded_install_folder(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn(r"C:\Projeler\QuantBIST", text)


if __name__ == "__main__":
    unittest.main()
