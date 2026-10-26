import os

# before any QuantBIST import configures logging
os.environ["QUANTBIST_LOG_FILE"] = ""

import pytest  # noqa: E402

from core.backtest import expectations  # noqa: E402
from core.market import store  # noqa: E402
from core.reports import health, runs  # noqa: E402


@pytest.fixture(autouse=True)
def _private_run_files(tmp_path, monkeypatch):
    """Tests never touch the real report lock, logs/runs.csv or data/market.db."""

    monkeypatch.setattr(runs, "LOCK_FILE", tmp_path / ".daily.lock")
    monkeypatch.setattr(runs, "RUNS_FILE", tmp_path / "runs.csv")

    def offline(*args, **kwargs):
        raise RuntimeError("no network in tests")

    monkeypatch.setattr(health, "_http_get", offline)
    # /performans reads the committed live reference; tests use their own or none
    monkeypatch.setattr(expectations, "EXPECTATIONS_FILE", tmp_path / "view_expectations.csv")

    previous = store._db_path
    store.configure(tmp_path / "market.db")
    yield
    store.configure(previous)


# The whole run must leave the real data/ and logs/ folders as it found them:
# nothing created, changed or deleted (tests/write_guard.py, tests/test_write_guard.py).
from core.config.paths import DATA_DIR, LOG_DIR  # noqa: E402
from tests.write_guard import changes, snapshot  # noqa: E402

_BEFORE = snapshot([DATA_DIR, LOG_DIR])


def pytest_sessionfinish(session, exitstatus):
    found = changes(_BEFORE, snapshot([DATA_DIR, LOG_DIR]))
    if found:
        print("\nTests touched the real data/ or logs/ folder:\n  " + "\n  ".join(found))
        session.exitstatus = 1
