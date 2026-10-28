"""
scripts/guncelle.py: the PC updater (Windows), now versioned in the repo. These tests cover
the decisions that need no Windows: which commit to install (only one whose CI passed, never
an older version), and when the result goes to Telegram (every outcome but "nothing new").
"""

import importlib.util
import json
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "scripts" / "guncelle.py"


def load():
    spec = importlib.util.spec_from_file_location("guncelle", PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # importing must not touch Windows, files or the network
    return module


g = load()


def api(*runs):
    return json.dumps({"total_count": len(runs), "workflow_runs": list(runs)}).encode()


class VersionTest(unittest.TestCase):
    def test_version_numbers_compare_as_numbers(self):
        self.assertEqual(g.version_of('__version__ = "0.67.0"\n'), "0.67.0")
        self.assertTrue(g.newer("0.10.0", "0.9.9"))
        self.assertFalse(g.newer("0.66.0", "0.66.0"))
        self.assertFalse(g.newer("0.65.0", "0.66.0"))  # never a downgrade
        with self.assertRaises(RuntimeError):
            g.version_of("no version here")


class GreenCommitTest(unittest.TestCase):
    def test_newest_successful_ci_run_of_the_branch(self):
        asked = []

        def fetch(url):
            asked.append(url)
            return api({"head_sha": "abc123", "head_branch": g.BRANCH, "conclusion": "success"})

        self.assertEqual(g.latest_green(fetch), "abc123")
        self.assertIn("status=success", asked[0])
        self.assertIn("branch=claude%2Fborsa-bot-creation-n7nmc9", asked[0])
        self.assertIn("/workflows/ci.yml/", asked[0])

    def test_no_green_run_or_another_branch_means_nothing_to_install(self):
        self.assertIsNone(g.latest_green(lambda url: api()))
        self.assertIsNone(g.latest_green(lambda url: api({"head_sha": "x", "head_branch": "main",
                                                           "conclusion": "success"})))
        self.assertIsNone(g.latest_green(lambda url: api({"head_sha": "x", "head_branch": g.BRANCH,
                                                           "conclusion": "failure"})))

    def test_files_come_from_that_exact_commit(self):
        self.assertIn("/abc123/core/__init__.py", g.version_url("abc123"))
        self.assertTrue(g.zip_url("abc123").endswith("/archive/abc123.zip"))


class NotifyTest(unittest.TestCase):
    def test_every_outcome_but_nothing_new_goes_to_telegram(self):
        for summary in ("KURULDU: v0.66.0 → v0.67.0", "KURULMADI: ...", "GERİ ALINDI: ...", "DURDU: ...",
                        "HATA: URLError: ..."):
            with self.subTest(summary):
                self.assertTrue(g.should_notify(summary))
        for summary in ("GÜNCEL: v0.67.0 kurulu, yeni sürüm yok.", "MEŞGUL: başka bir güncelleme sürüyor"):
            with self.subTest(summary):
                self.assertFalse(g.should_notify(summary))


class BildirTest(unittest.TestCase):
    def test_bildir_is_in_the_repo_and_reads_no_secret_itself(self):
        text = (PATH.parent / "bildir.py").read_text(encoding="utf-8")
        self.assertIn("require_bot_settings", text)  # token and chat id come from .env
        self.assertNotRegex(text, r"\d{8,10}:[A-Za-z0-9_-]{30,}")


if __name__ == "__main__":
    unittest.main()
