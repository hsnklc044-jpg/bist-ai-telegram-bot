"""CHARTER I2: the repository is public. No .env, token, monitoring address or personal record may be committed.
Runs in CI on every push (the checkout is a git repository); skipped where git is not available."""

import re
import subprocess
import unittest
from pathlib import Path

from core.backup import PERSONAL_FILES
from core.config.paths import MARKET_DB

ROOT = Path(__file__).resolve().parents[1]
TOKEN = re.compile(rb"\b\d{8,10}:AA[A-Za-z0-9_-]{30,40}\b")  # Telegram bot token shape
PING = re.compile(rb"hc-ping\.com/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")  # Healthchecks UUID


def tracked() -> list[str]:
    try:
        out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True, timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        raise unittest.SkipTest("not a git checkout (git ls-files failed)") from None
    return [p for p in out.decode("utf-8").split("\0") if p]


class RepoSecretsTest(unittest.TestCase):
    def test_no_env_or_personal_record_is_tracked(self):
        files = set(tracked())
        forbidden = {".env", *(str(p.relative_to(ROOT)).replace("\\", "/") for p in (*PERSONAL_FILES, MARKET_DB))}
        self.assertEqual(sorted(files & forbidden), [])
        self.assertEqual([f for f in files if f.startswith(("data/backups/", "logs/"))], [])

    def test_no_token_or_monitoring_address_in_any_tracked_file(self):
        found = []
        for name in tracked():
            path = ROOT / name
            if not path.is_file() or path.stat().st_size > 5_000_000:
                continue
            body = path.read_bytes()
            if TOKEN.search(body) or PING.search(body):
                found.append(name)
        self.assertEqual(found, [])

    def test_patterns_catch_the_real_shapes(self):
        self.assertTrue(TOKEN.search(b"BOT_TOKEN=1234567890:AAH" + b"x" * 32))
        # built at run time, so this file itself never contains a matching address
        self.assertTrue(PING.search(b"https://hc-ping.com/" + b"-".join([b"0f1e2d3c", b"4b5a", b"6978", b"8796",
                                                                           b"a5b4c3d2e1f0"])))
        self.assertFalse(TOKEN.search(b'token("123:ABC")'))


if __name__ == "__main__":
    unittest.main()
