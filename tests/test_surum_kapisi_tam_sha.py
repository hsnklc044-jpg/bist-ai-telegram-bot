"""Finding 8 (19.11.2026): the gate must resolve a short SHA to the full one before the CI query.

GitHub's head_sha filter matches only a full SHA; a short one returns zero runs and the gate wrongly
reports "no CI run" (22:07 incident). Write the test first; it fails until resolve_full_sha exists.
"""

import importlib.util
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("surum_kapisi", ROOT / "scripts" / "surum_kapisi.py")
kapi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kapi)


def test_short_sha_resolves_to_full():
    full = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8").stdout.strip()
    assert kapi.resolve_full_sha(full[:7], cwd=ROOT) == full


def test_full_sha_is_unchanged():
    full = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8").stdout.strip()
    assert kapi.resolve_full_sha(full, cwd=ROOT) == full


def test_unknown_sha_returns_none():
    assert kapi.resolve_full_sha("deadbee0000", cwd=ROOT) is None
