"""
QuantBIST
Finding 7 (DERS_DEFTERI 19.11): the live-path PreToolUse hook must also catch Bash/PowerShell writes into the
live install when the target path is relative and the session's working directory (or a `cd` in the command)
is the live folder. Reads, `2>$null`, `2>&1` and writes to other absolute folders stay allowed.
The hook's repo copy is `scripts/hooks/canli_koruma.py`; the active copy lives outside the repo.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / "scripts" / "hooks" / "canli_koruma.py"
_spec = importlib.util.spec_from_file_location("canli_koruma", HOOK)
canli = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(canli)

LIVE_CWD = r"C:\Projeler\QuantBIST-yeni"
OTHER_CWD = r"C:\Projeler\QuantBIST-araclar\wt-x"


def _decide(tool: str, command: str, cwd: str = LIVE_CWD):
    return canli.decide({"tool_name": tool, "tool_input": {"command": command}, "cwd": cwd})


DENY = [
    # the 19.11 incident shape: empty file created by a redirect, relative path, live cwd
    ("PowerShell", '"" > tests\\test_research_workflow_pause.py'),
    ("PowerShell", "echo x >> data\\a.txt"),
    ("Bash", "echo x > tests/test_a.py"),
    ("Bash", "cat > notes.md <<'EOF'\nx\nEOF"),
    ("PowerShell", "New-Item -ItemType File tests\\x.py"),
    ("PowerShell", "Set-Content x.txt 1"),
    ("PowerShell", "Out-File -FilePath a.md -InputObject 1"),
    ("Bash", "echo x | tee out.txt"),
    ("Bash", "touch a.py"),
    ("PowerShell", 'Get-Date | Out-File "rapor.txt"'),
]

ALLOW = [
    ("PowerShell", "git log -1 --format=%H 2>$null"),
    ("PowerShell", "git status --short 2>&1"),
    ("Bash", "git log -1 > /dev/null"),
    ("PowerShell", "Get-Content logs\\heartbeats.csv -Tail 3 > $null"),
    ("PowerShell", "Add-Content -Path C:\\Projeler\\QuantBIST-araclar\\cikti\\OTONOM_RAPOR.md -Value x"),
    ("PowerShell", "git log -1 > C:\\Users\\hsnkl\\AppData\\Local\\Temp\\x.txt"),
    ("Bash", 'python -c "print(1 > 0)"'),
    ("PowerShell", "Select-String -Path logs\\quantbist.log -Pattern 'a -> b'"),
    ("Bash", "echo 'x > y'"),
    ("PowerShell", "Remove-Item $env:TEMP\\tck_old.py -Force"),
    ("Bash", "cat > /c/Users/x/a.md <<'EOF'\n> alinti satiri\nEOF"),
    ("PowerShell", "git commit -m @'\nv1 -> v2\n'@"),
]


@pytest.mark.parametrize("tool,command", DENY)
def test_relative_write_in_live_cwd_is_denied(tool, command):
    assert _decide(tool, command) is not None, command


@pytest.mark.parametrize("tool,command", ALLOW)
def test_reads_and_elsewhere_writes_in_live_cwd_are_allowed(tool, command):
    assert _decide(tool, command) is None, command


@pytest.mark.parametrize("tool,command", DENY)
def test_relative_write_outside_live_cwd_is_allowed(tool, command):
    assert _decide(tool, command, cwd=OTHER_CWD) is None, command


@pytest.mark.parametrize(
    "command",
    [
        "cd C:\\Projeler\\QuantBIST-yeni; echo x > tests\\a.py",
        "cd /c/Projeler/QuantBIST-yeni && echo x > tests/a.py",
        "Set-Location C:\\Projeler\\QuantBIST-yeni; New-Item a.txt",
    ],
)
def test_cd_into_live_then_relative_write_is_denied(command):
    assert _decide("PowerShell", command, cwd=OTHER_CWD) is not None


def test_existing_absolute_rules_still_hold():
    assert _decide("Bash", "echo a > /c/Projeler/QuantBIST-yeni/data/x.txt", cwd=OTHER_CWD) is not None
    assert _decide("Bash", "git push --force origin x", cwd=OTHER_CWD) is not None
    assert _decide("PowerShell", "git push origin claude/x", cwd=OTHER_CWD) is None
