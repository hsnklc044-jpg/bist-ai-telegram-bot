"""
scripts/yeni_kurulum.ps1 (03.11.2026): the clean install next to the user's old folder. It must
never overwrite the new folder, never touch the old one, never replace a release file with an
old copy, keep the token out of the script, and stay ASCII for Windows PowerShell 5.1.
"""

import unittest

from core.config.paths import ROOT_DIR

SCRIPT = ROOT_DIR / "scripts" / "yeni_kurulum.ps1"


class InstallScriptTest(unittest.TestCase):
    def setUp(self):
        self.text = SCRIPT.read_text(encoding="utf-8")
        self.code = "\n".join(line for line in self.text.splitlines() if not line.lstrip().startswith("#"))

    def test_safe(self):
        self.assertIn("if (Test-Path $New) { Fail", self.code)  # an existing folder stops it
        for verb in ("Remove-Item", "Stop-Process", "Move-Item", "del ", "rmdir", "/MIR", "/PURGE"):
            self.assertNotIn(verb, self.code)
        self.assertIn("/XC /XN /XO", self.code)  # only files the release does not have

    def test_no_secret_and_ascii(self):
        self.assertTrue(self.text.isascii())
        for word in ("TELEGRAM_BOT_TOKEN=", "bot_token", "chat_id="):
            self.assertNotIn(word, self.text)


if __name__ == "__main__":
    unittest.main()
