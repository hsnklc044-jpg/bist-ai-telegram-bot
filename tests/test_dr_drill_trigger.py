"""12.11.2026: a branch that changes an updater/backup/restore/record-format file runs dr-drill by itself on push,
so the gate's "dr-drill on the same SHA" needs no manual start (no gh, no token on the PC)."""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "dr-drill.yml"


def _alone() -> set[str]:
    tree = ast.parse((ROOT / "scripts" / "surum_kapisi.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "ALONE" for t in node.targets):
            return set(ast.literal_eval(node.value))
    raise AssertionError("ALONE not found")


def _on_block() -> str:
    text = WORKFLOW.read_text(encoding="utf-8")
    return re.search(r"^on:\n((?:[ #].*\n|\n)*)", text, re.M).group(1)


def _push_paths() -> set[str]:
    block = re.search(r"^  push:\n((?:    .*\n)*)", _on_block(), re.M)
    assert block, "no push trigger"
    return set(re.findall(r'^\s+- "([^"]+)"', block.group(1), re.M))


def test_every_alone_file_triggers_the_drill_on_push():
    paths = _push_paths()
    assert _alone() <= paths, sorted(_alone() - paths)
    assert ".github/workflows/dr-drill.yml" in paths


def test_manual_and_monthly_runs_stay():
    on = _on_block()
    assert "  workflow_dispatch:" in on and "  schedule:" in on
