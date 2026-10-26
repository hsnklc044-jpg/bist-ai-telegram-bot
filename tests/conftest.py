import os

# before any QuantBIST import configures logging
os.environ["QUANTBIST_LOG_FILE"] = ""

import pytest  # noqa: E402

from core.market import store  # noqa: E402
from core.reports import runs  # noqa: E402


@pytest.fixture(autouse=True)
def _private_run_files(tmp_path, monkeypatch):
    """Tests never touch the real report lock, logs/runs.csv or data/market.db."""

    monkeypatch.setattr(runs, "LOCK_FILE", tmp_path / ".daily.lock")
    monkeypatch.setattr(runs, "RUNS_FILE", tmp_path / "runs.csv")

    previous = store._db_path
    store.configure(tmp_path / "market.db")
    yield
    store.configure(previous)


# The whole run must leave the real data/ and logs/ folders as it found them.
from core.config.paths import DATA_DIR, LOG_DIR  # noqa: E402


def _listing() -> set[str]:
    return {str(p) for folder in (DATA_DIR, LOG_DIR) if folder.exists() for p in folder.rglob("*")}


_BEFORE = _listing()


def pytest_sessionfinish(session, exitstatus):
    created = sorted(_listing() - _BEFORE)
    if created:
        print("\nTests created files in the real data/ or logs/ folder:\n  " + "\n  ".join(created))
        session.exitstatus = 1
