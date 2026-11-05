"""
scripts/guncelle.py: the PC updater (Windows), now versioned in the repo. These tests cover
the decisions that need no Windows: which commit to install (only one whose CI passed, never
an older version), and when the result goes to Telegram (every outcome but "nothing new").
"""

import importlib.util
import json
import unittest
import unittest.mock
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


class HeadersTest(unittest.TestCase):
    def test_github_api_header_only_for_the_api(self):
        """Öz-tarama v0.68: the zip and raw file requests must not carry the API's Accept header."""
        sent = {}

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def read(self):
                return b"ok"

        def opener(request, timeout):
            sent[request.full_url] = request.get_header("Accept")
            return Response()

        with unittest.mock.patch("urllib.request.urlopen", opener):
            g.fetch(g.zip_url("abc"))
            g.fetch(g.version_url("abc"))
            g.fetch(g.API + "?x=1")
        self.assertIsNone(sent[g.zip_url("abc")])
        self.assertIsNone(sent[g.version_url("abc")])
        self.assertEqual(sent[g.API + "?x=1"], "application/vnd.github+json")


class NotifyTest(unittest.TestCase):
    def test_every_outcome_but_nothing_new_goes_to_telegram(self):
        for summary in ("KURULDU: v0.66.0 → v0.67.0", "KURULMADI: ...", "GERİ ALINDI: ...", "DURDU: ...",
                        "HATA: URLError: ..."):
            with self.subTest(summary):
                self.assertTrue(g.should_notify(summary))
        for summary in ("GÜNCEL: v0.67.0 kurulu, yeni sürüm yok.", "MEŞGUL: başka bir güncelleme sürüyor"):
            with self.subTest(summary):
                self.assertFalse(g.should_notify(summary))


class GitFolderTest(unittest.TestCase):
    """04.11.2026: the PC runs from a git clone (C:\\Projeler\\QuantBIST-yeni); the updater was fixed to
    the old folder and copied zips, which would leave a git clone dirty."""

    def test_the_project_is_the_folder_the_script_is_in(self):
        self.assertEqual(g.PROJECT, PATH.resolve().parents[1])
        self.assertEqual(g.PYTHON, g.PROJECT / ".venv" / "Scripts" / "python.exe")

    def calls(self, outputs):
        seen = []

        def run(cmd, cwd, timeout=900):
            seen.append(cmd[1:] if cmd[0] == "git" else cmd)
            out, code = outputs.get(cmd[1] if cmd[0] == "git" else "", ("", 0))
            return unittest.mock.Mock(stdout=out, stderr="", returncode=code)

        return seen, run

    def test_clean_clone_is_fast_forwarded_to_the_green_commit(self):
        seen, run = self.calls({"branch": (g.BRANCH, 0), "rev-parse": ("abc123\n", 0)})
        old, error = g.apply_git(Path("."), "f00d", run=run)
        self.assertEqual((old, error), ("abc123", None))
        self.assertIn(["status", "--porcelain", "--untracked-files=no"], seen)
        self.assertIn(["fetch", "origin", g.BRANCH], seen)
        self.assertEqual(seen[-1], ["merge", "--ff-only", "f00d"])

    def test_local_changes_stop_the_update(self):
        seen, run = self.calls({"branch": (g.BRANCH, 0), "status": (" M core/x.py\n", 0), "rev-parse": ("abc123\n", 0)})
        old, error = g.apply_git(Path("."), "f00d", run=run)
        self.assertIn("yerel değişiklik", error)
        self.assertFalse(any(c[:1] == ["merge"] for c in seen))  # nothing changed

    def test_another_branch_is_never_moved(self):
        seen, run = self.calls({"branch": ("main\n", 0), "rev-parse": ("abc\n", 0)})
        self.assertIn("dal", g.apply_git(Path("."), "f00d", run=run)[1])
        self.assertFalse(any(c[:1] == ["merge"] for c in seen))

    def test_failed_merge_is_reported(self):
        seen, run = self.calls({"branch": (g.BRANCH, 0), "merge": ("not possible to fast-forward", 1), "rev-parse": ("abc\n", 0)})
        self.assertIn("ileri sarılamadı", g.apply_git(Path("."), "f00d", run=run)[1])

    def test_rollback_returns_to_the_old_commit(self):
        seen, run = self.calls({})
        g.rollback_git(Path("."), "abc123", run=run)
        self.assertEqual(seen, [["reset", "--hard", "abc123"]])


class QuietHoursTest(unittest.TestCase):
    def test_not_while_the_report_runs(self):
        from datetime import datetime

        self.assertTrue(g.report_window(datetime(2026, 11, 4, 18, 0)))
        self.assertTrue(g.report_window(datetime(2026, 11, 4, 19, 59)))
        self.assertFalse(g.report_window(datetime(2026, 11, 4, 20, 0)))
        self.assertFalse(g.report_window(datetime(2026, 11, 4, 7, 40)))
        self.assertFalse(g.should_notify("BEKLİYOR: rapor saati"))


class NetworkWaitTest(unittest.TestCase):
    """04.11.2026: the hourly task failed at 09:40, 10:40 and 11:40 with getaddrinfo while the network
    worked by hand: the first request is retried after 30 s, 1 and 2 minutes."""

    def test_a_late_network_is_waited_for(self):
        import urllib.error

        answers = iter([urllib.error.URLError("getaddrinfo failed"), OSError("x"), "sha"])
        waits = []

        def latest():
            a = next(answers)
            if isinstance(a, Exception):
                raise a
            return a

        self.assertEqual(g.with_network(latest, sleep=waits.append), "sha")
        self.assertEqual(waits, [30, 60])

    def test_no_network_says_so(self):
        import urllib.error

        def latest():
            raise urllib.error.URLError("getaddrinfo failed")

        waits = []
        with self.assertRaises(g.NoNetwork):
            g.with_network(latest, sleep=waits.append)
        self.assertEqual(waits, [30, 60, 120])
        self.assertFalse(g.should_notify("BAĞLANTI YOK: GitHub'a ulaşılamadı"))  # Telegram would fail too


class BotDetectionTest(unittest.TestCase):
    """04.11.2026: the bot was looked for under 'QuantBIST\\.venv' (the old folder); from QuantBIST-yeni it
    was never found, so v0.99.59 was rolled back and 'BOT KAPALI' reported while it ran."""

    def test_the_bot_of_this_folder_is_found(self):
        import re

        pattern = g.bot_pattern(Path(r"C:\Projeler\QuantBIST-yeni"))
        new = r'"C:\Projeler\QuantBIST-yeni\.venv\Scripts\pythonw.exe" main.py'
        old = r'"C:\Projeler\QuantBIST\.venv\Scripts\pythonw.exe" main.py'
        self.assertTrue(re.search(pattern, new, flags=re.I))
        self.assertFalse(re.search(pattern, old, flags=re.I))  # another folder's bot is not this one


class LockCompareTest(unittest.TestCase):
    """04.11.2026: every install said "paketler güncellendi": the git clone on Windows has CRLF, the
    GitHub zip LF, and the lock files were compared byte by byte."""

    def test_line_endings_do_not_count(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a.lock", Path(tmp) / "b.lock"
            a.write_bytes(b"pandas==2.2.3\r\nnumpy==2.1.0\r\n")
            b.write_bytes(b"pandas==2.2.3\nnumpy==2.1.0\n")
            self.assertFalse(g.locks_differ(a, b))
            b.write_bytes(b"pandas==2.2.4\nnumpy==2.1.0\n")
            self.assertTrue(g.locks_differ(a, b))


class TaskScriptTest(unittest.TestCase):
    def test_registration_runs_hourly_from_this_folder(self):
        text = (PATH.parent / "register_update_task.ps1").read_text(encoding="utf-8")
        self.assertIn("QuantBIST Guncelle", text)
        self.assertIn("$PSScriptRoot", text)  # the folder the script is in, never a fixed path
        self.assertIn("RepetitionInterval", text)
        self.assertIn("07:40", text)


class BildirTest(unittest.TestCase):
    def test_bildir_is_in_the_repo_and_reads_no_secret_itself(self):
        text = (PATH.parent / "bildir.py").read_text(encoding="utf-8")
        self.assertIn("require_bot_settings", text)  # token and chat id come from .env
        self.assertNotRegex(text, r"\d{8,10}:[A-Za-z0-9_-]{30,}")


if __name__ == "__main__":
    unittest.main()


class FailedTestNamesTest(unittest.TestCase):
    """05.11.2026: the Telegram line said "1 failed" without its name; the PC's data made it fail."""

    def test_failed_names_are_kept_short(self):
        out = ("....F..\n=========================== short test summary info ============================\n"
               "FAILED tests/test_a.py::ATest::test_one - AssertionError: x\n"
               "FAILED tests/test_b.py::BTest::test_two - ValueError: y\n"
               "1 failed, 1300 passed in 1354.32s\n")
        self.assertEqual(g.failed_names(out), "test_a.py::ATest::test_one, test_b.py::BTest::test_two")

    def test_more_than_three_are_counted(self):
        out = "".join(f"FAILED tests/t.py::T::test_{i} - E\n" for i in range(5))
        self.assertTrue(g.failed_names(out).endswith("(+2)"))

    def test_none(self):
        self.assertEqual(g.failed_names("5 passed\n"), "")
