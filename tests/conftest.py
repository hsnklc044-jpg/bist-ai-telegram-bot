import pytest

from core.reports import runs


@pytest.fixture(autouse=True)
def _private_run_files(tmp_path, monkeypatch):
    """Tests never touch the real report lock or logs/runs.csv."""

    monkeypatch.setattr(runs, "LOCK_FILE", tmp_path / ".daily.lock")
    monkeypatch.setattr(runs, "RUNS_FILE", tmp_path / "runs.csv")
