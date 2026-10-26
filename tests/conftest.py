import os

# before any QuantBIST import configures logging
os.environ["QUANTBIST_LOG_FILE"] = ""

import pytest  # noqa: E402

from core.reports import runs  # noqa: E402


@pytest.fixture(autouse=True)
def _private_run_files(tmp_path, monkeypatch):
    """Tests never touch the real report lock or logs/runs.csv."""

    monkeypatch.setattr(runs, "LOCK_FILE", tmp_path / ".daily.lock")
    monkeypatch.setattr(runs, "RUNS_FILE", tmp_path / "runs.csv")
