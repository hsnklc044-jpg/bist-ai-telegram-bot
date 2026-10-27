"""
The lock file must pin every direct dependency, and the running
interpreter must be the supported version.
"""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _names(path: Path) -> set[str]:
    names = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or line.startswith("-r"):
            continue
        names.add(re.split(r"[<>=!~\[ ;]", line, maxsplit=1)[0].lower().replace("_", "-"))
    return names


class EnvironmentTest(unittest.TestCase):
    def test_lock_pins_every_dependency(self):
        lock = ROOT / "requirements.lock"
        pinned = {}
        for line in lock.read_text(encoding="utf-8").splitlines():
            if line and not line.startswith("#"):
                self.assertIn("==", line, f"not pinned: {line}")
                name, version = line.split("==", 1)
                pinned[name.lower().replace("_", "-")] = version

        wanted = _names(ROOT / "requirements.txt") | _names(ROOT / "requirements-dev.txt")
        self.assertEqual(wanted - set(pinned), set(), "missing from requirements.lock")

    def test_supported_python(self):
        self.assertGreaterEqual(sys.version_info[:2], (3, 11))


class VersionTest(unittest.TestCase):
    def test_package_version_matches_pyproject(self):
        import tomllib

        from core import __version__

        meta = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(__version__, meta["project"]["version"])


if __name__ == "__main__":
    unittest.main()


class LocalWorkFoldersTest(unittest.TestCase):
    """The user keeps backups/, qb/ and research_workspace/ in the live folder (not in the repo).
    setup.ps1/verify.ps1 run `ruff check .` there: those folders must not fail the check."""

    def test_ruff_skips_local_work_folders(self):
        import shutil
        import subprocess
        import tempfile

        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copy(root / "pyproject.toml", tmp)
            for folder in ("backups", "qb", "research_workspace/ohlc_audit"):
                (Path(tmp) / folder).mkdir(parents=True)
                (Path(tmp) / folder / "x.py").write_text("from pathlib import Path\nimport os\nimport json\n",
                                                         encoding="utf-8")  # unsorted, unused
            result = subprocess.run([sys.executable, "-m", "ruff", "check", "."], cwd=tmp,
                                    capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
