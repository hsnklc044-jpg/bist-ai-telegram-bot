"""
QuantBIST
K-116: the weekly research workflow's rule-test steps (research, research on today's list, research with
price fixes, phase3, a4, candidates --pit) stay off until the 18.12.2026 package; the data steps
(prices, USD/TRY) keep running. Each paused step carries `if: false` with a K-116 note so that the
18.12 package re-enables it by removing that one line (and updating this test).
"""

from __future__ import annotations

import re
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "research.yml"
RULE_TEST = re.compile(r"python -m core\.backtest\.(research|phase3|a4|candidates)\b")
DATA = ("core.market.update", "core.market.macro")
PAUSED = re.compile(r"(?m)^ {8}if: false\s+# K-116\b")


def _steps() -> list[str]:
    text = WORKFLOW.read_text(encoding="utf-8")
    body = text.split("\n    steps:\n", 1)[1]
    return re.split(r"(?m)^ {6}- ", body)[1:]


def test_rule_test_steps_are_paused():
    found = [s for s in _steps() if RULE_TEST.search(s)]
    assert len(found) == 6, [s.splitlines()[0] for s in found]
    running = [s.splitlines()[0] for s in found if not PAUSED.search(s)]
    assert not running, f"K-116: these rule-test steps can still run before 18.12.2026: {running}"


def test_data_steps_keep_running():
    for command in DATA:
        steps = [s for s in _steps() if command in s]
        assert len(steps) == 1, command
        assert not re.search(r"(?m)^ {8}if:", steps[0]), command


def test_pause_is_explained_in_reports():
    steps = _steps()
    note = [s for s in steps if s.startswith("name: K-116 pause note")]
    assert len(note) == 1 and not re.search(r"(?m)^ {8}if:", note[0])
    for name in ("research", "research_today", "research_fixed", "phase3", "a4", "candidates"):
        assert re.search(rf"for f in [^\n]*\b{name}\b", note[0]), name
    compare = [s for s in steps if "python -m core.backtest.history" in s]
    assert len(compare) == 1 and "K-116" in compare[0] and "if: always()" in compare[0]


def test_no_other_step_is_paused():
    for s in _steps():
        if not RULE_TEST.search(s):
            assert not PAUSED.search(s), s.splitlines()[0]
