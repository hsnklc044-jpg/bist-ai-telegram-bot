"""Finding 8 (19.11.2026): the gate must resolve a short SHA to the full one before the CI query.

GitHub's head_sha filter matches only a full SHA; a short one returns zero runs and the gate wrongly
reports "no CI run" (22:07 incident). Write the test first; it fails until resolve_full_sha exists.

Finding 14 (21.11.2026): the updater's stage copy (Temp quantbist_stage_*, robocopy, no .git) runs
the full suite too. The first version of these tests read HEAD of the project repo, so they passed in
the worktree and CI but failed in the stage copy and blocked v0.99.161 four times. The tests below
build their own throwaway repo, and test_suite_passes_in_non_git_copy reproduces the stage copy.
"""

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("surum_kapisi", ROOT / "scripts" / "surum_kapisi.py")
kapi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kapi)

_GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t"}


def _git(args, cwd):
    env = {**os.environ, **_GIT_ENV, "GIT_CEILING_DIRECTORIES": str(Path(cwd).parent)}
    # No global signing/hooks can break the throwaway commit (red team 21.11, item 1).
    return subprocess.run(["git", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=",
                           "-c", "init.defaultBranch=main", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                          env=env, check=True).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    """A one-commit repo of its own; independent of whether the project copy has .git."""
    if shutil.which("git") is None:
        pytest.skip("git yok")
    _git(["init", "-q"], tmp_path)
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    _git(["add", "a.txt"], tmp_path)
    _git(["commit", "-q", "-m", "a"], tmp_path)
    return tmp_path, _git(["rev-parse", "HEAD"], tmp_path)


def test_short_sha_resolves_to_full(repo):
    path, full = repo
    assert kapi.resolve_full_sha(full[:7], cwd=path) == full


def test_full_sha_is_unchanged(repo):
    path, full = repo
    assert kapi.resolve_full_sha(full, cwd=path) == full


def test_unknown_sha_returns_none(repo):
    path, _ = repo
    assert kapi.resolve_full_sha("deadbee0000", cwd=path) is None


def test_non_git_dir_returns_none(tmp_path, monkeypatch):
    if shutil.which("git") is None:
        pytest.skip("git yok")
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))
    assert kapi.resolve_full_sha("deadbee", cwd=tmp_path) is None


@pytest.mark.skipif(os.environ.get("QB_STAGE_SIM") == "1", reason="already inside the simulated copy")
def test_suite_passes_in_non_git_copy(tmp_path):
    """Protection: this file must pass in a copy without .git, like the updater's stage copy."""
    (tmp_path / "tests").mkdir()
    (tmp_path / "scripts").mkdir()
    shutil.copy2(Path(__file__), tmp_path / "tests" / Path(__file__).name)
    shutil.copy2(ROOT / "scripts" / "surum_kapisi.py", tmp_path / "scripts" / "surum_kapisi.py")
    env = {**os.environ, "QB_STAGE_SIM": "1", "GIT_CEILING_DIRECTORIES": str(tmp_path.parent)}
    res = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests"],
                         cwd=tmp_path, capture_output=True, text=True, encoding="utf-8", env=env, timeout=300)
    assert res.returncode == 0, res.stdout[-2000:]
