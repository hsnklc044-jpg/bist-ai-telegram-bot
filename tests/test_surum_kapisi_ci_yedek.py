"""Repair queue 3 (24.11.2026, finding 8): when the head_sha query returns no CI run, the gate retries
by branch and matches the SHA itself, instead of wrongly reporting "no CI run" (a false red delays installs).
Red first: fails until _ci falls back to the branch query."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("surum_kapisi", ROOT / "scripts" / "surum_kapisi.py")
kapi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kapi)

SHA = "a" * 40
OTHER = "b" * 40


def _run(sha, conclusion="success", name="CI"):
    return {"name": name, "head_sha": sha, "status": "completed", "conclusion": conclusion,
            "html_url": f"https://example.test/{sha[:7]}"}


def _fake(monkeypatch, by_sha, by_branch, branches=("claude/x",)):
    calls = []

    def fake_get(url):
        calls.append(url)
        if "head_sha=" in url:
            return {"workflow_runs": by_sha}
        return {"workflow_runs": by_branch}

    monkeypatch.setattr(kapi, "_get_json", fake_get, raising=False)
    monkeypatch.setattr(kapi, "_branches_of", lambda sha: list(branches), raising=False)
    return calls


def test_fallback_finds_run_when_sha_query_is_empty(monkeypatch):
    calls = _fake(monkeypatch, [], [_run(OTHER), _run(SHA)])
    ok, text = kapi._ci(SHA)
    assert ok is True
    assert "success" in text
    assert any("branch=claude" in c for c in calls)


def test_fallback_ignores_runs_of_other_shas(monkeypatch):
    _fake(monkeypatch, [], [_run(OTHER)])
    ok, text = kapi._ci(SHA)
    assert ok is False
    assert "yok" in text


def test_fallback_never_turns_a_red_run_green(monkeypatch):
    _fake(monkeypatch, [], [_run(SHA, conclusion="failure")])
    ok, _ = kapi._ci(SHA)
    assert ok is False


def test_sha_query_result_is_used_without_fallback(monkeypatch):
    calls = _fake(monkeypatch, [_run(SHA)], [])
    ok, _ = kapi._ci(SHA)
    assert ok is True
    assert not any("branch=" in c for c in calls)
