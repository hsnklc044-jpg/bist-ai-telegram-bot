"""
scripts/pull_backups.sh against a stand-in server: scp and ssh are replaced by
small shims that work on a local folder, so the script's own steps are tested:
copy, check with the restore test, and only then write pulled.txt on the server.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from core import backup
from core.market.calendar import ISTANBUL
from core.reports import health

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "pull_backups.sh"

SCP = """#!/usr/bin/env bash
# scp -q host:path/glob dest  ->  cp from $FAKE_SERVER/path
src="${@: -2:1}"; dest="${@: -1}"
cp $FAKE_SERVER/${src#*:} "$dest"
"""
SSH = """#!/usr/bin/env bash
# ssh host "command"  ->  run it in $FAKE_SERVER
cd "$FAKE_SERVER" && bash -c "${@: -1}"
"""


# on Windows "bash" may be WSL's stub with no distribution installed (DR drill 27.10, run 40550012681)
@unittest.skipUnless(os.name != "nt" and shutil.which("bash"), "bash is needed (Linux/macOS; Windows uses pull_backups.ps1)")
class PullBackupsTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.server = self.root / "server"
        self.remote = self.server / "QuantBIST" / "backups"
        self.local = self.root / "pc"
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        for name, text in (("scp", SCP), ("ssh", SSH)):
            path = bin_dir / name
            path.write_text(text, encoding="utf-8")
            path.chmod(0o755)
        ledger = self.root / "ledger.csv"
        ledger.write_text("id,date,account,symbol,side,quantity,price,fee,note\n"
                          "1,2026-06-01,real,AAA.IS,buy,100,50,5,\n", encoding="utf-8")
        self.backup = backup.create_backup([ledger], target=self.remote, name="quantbist_2026-10-26.zip")
        self.env = {**os.environ, "SCP": str(bin_dir / "scp"), "SSH": str(bin_dir / "ssh"),
                    "FAKE_SERVER": str(self.server), "PYTHON": sys.executable, "QUANTBIST_LOG_FILE": ""}

    def run_script(self):
        return subprocess.run(["bash", str(SCRIPT), "kullanici@sunucu", "QuantBIST/backups", str(self.local)],
                              env=self.env, capture_output=True, text=True, encoding="utf-8", timeout=120)

    def test_copies_checks_and_marks_the_server(self):
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((self.local / "quantbist_2026-10-26.zip").exists())
        self.assertIn("Geri yükleme testi başarılı", result.stdout)
        marker = self.remote / health.PULL_MARKER
        pulled = datetime.fromisoformat(marker.read_text(encoding="utf-8").strip())
        self.assertLess(abs(datetime.now(ISTANBUL) - pulled), timedelta(minutes=5))

    def test_damaged_backup_is_not_marked_as_pulled(self):
        data = bytearray(self.backup.path.read_bytes())
        data[len(data) // 2] ^= 0xFF
        self.backup.path.write_bytes(bytes(data))
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.remote / health.PULL_MARKER).exists())


if __name__ == "__main__":
    unittest.main()
