"""Gate row 5: a merge the updater will never install is not a pending package (18.11.2026).

The updater installs only when the version in pyproject.toml grows. A docs/tests merge that keeps the version
(0af56f3) leaves the bot branch ahead of the live checkout for good, and row 5 (`tip == head`) then never opens.
"""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("surum_kapisi", ROOT / "scripts" / "surum_kapisi.py")
kapi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kapi)


def test_same_sha_has_nothing_pending():
    assert kapi.nothing_pending("abc", "abc", "0.99.144", "0.99.144")


def test_same_version_ahead_is_not_pending():
    assert kapi.nothing_pending("0af56f3", "b1ab854", "0.99.144", "0.99.144")


def test_higher_version_waiting_for_the_updater_is_pending():
    assert not kapi.nothing_pending("5b26b1b", "0af56f3", "0.99.146", "0.99.144")


def test_unreadable_version_is_pending():
    assert not kapi.nothing_pending("5b26b1b", "0af56f3", None, "0.99.144")
