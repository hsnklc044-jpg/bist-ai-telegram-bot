import os

# before any QuantBIST import configures logging
os.environ["QUANTBIST_LOG_FILE"] = ""

import pytest  # noqa: E402

from core import signals_log  # noqa: E402
from core.alerts import levels  # noqa: E402
from core.analytics import levels as levels_module  # noqa: E402
from core.backtest import expectations  # noqa: E402
from core.fundamentals import store as fundamentals  # noqa: E402
from core.infrastructure import ping  # noqa: E402
from core.market import macro, store  # noqa: E402
from core.reports import daily, forward, health, runs, slo  # noqa: E402
from core.screen import command as screen  # noqa: E402
from core.screen import subscriptions, virtual  # noqa: E402


def pytest_collection_modifyitems(config, items):
    """QB_SHUFFLE_SEED=<n>: run the tests in a seeded random order (CI's slow-machine job), so a
    test that only passes after another one, or a race a slow PC shows (D12), is caught in CI too.
    The seed is printed; the same seed gives the same order."""

    seed = os.environ.get("QB_SHUFFLE_SEED")
    if seed:
        import random

        random.Random(seed).shuffle(items)
        print(f"\ntest sırası karıştırıldı: QB_SHUFFLE_SEED={seed}")


@pytest.fixture(autouse=True)
def _private_run_files(tmp_path, monkeypatch):
    """Tests never touch the real report lock, logs/runs.csv or data/market.db."""

    monkeypatch.setattr(runs, "LOCK_FILE", tmp_path / ".daily.lock")
    monkeypatch.setattr(runs, "RUNS_FILE", tmp_path / "runs.csv")

    def offline(*args, **kwargs):
        raise RuntimeError("no network in tests")

    monkeypatch.setattr(health, "_http_get", offline)
    # with HC_*_URL in the user's .env, a test must never ping (a /fail would page the user)
    monkeypatch.setattr(ping, "_http_get", offline)
    # /performans reads the committed live reference; tests use their own or none
    monkeypatch.setattr(expectations, "EXPECTATIONS_FILE", tmp_path / "view_expectations.csv")
    # SLO records (heartbeats, freshness, restore tests) and the monitoring state stay private too
    monkeypatch.setattr(slo, "HEARTBEATS_FILE", tmp_path / "heartbeats.csv")
    monkeypatch.setattr(slo, "FRESHNESS_FILE", tmp_path / "freshness.csv")
    monkeypatch.setattr(slo, "RESTORE_FILE", tmp_path / "restore_tests.csv")
    monkeypatch.setattr(ping, "STATE_FILE", tmp_path / "monitoring.json")
    monkeypatch.setattr(daily, "REPORT_TEXT_DIR", tmp_path / "reports")
    monkeypatch.setattr(levels, "PRICE_ALARMS_FILE", tmp_path / "price_alarms.csv")
    monkeypatch.setattr(screen, "SCREENS_FILE", tmp_path / "screens.csv")
    monkeypatch.setattr(subscriptions, "SUBSCRIPTIONS_FILE", tmp_path / "screen_subscriptions.csv")
    monkeypatch.setattr(subscriptions, "STATE_FILE", tmp_path / "screen_subscriptions_state.json")
    monkeypatch.setattr(virtual, "VIRTUAL_FILE", tmp_path / "screen_virtual.csv")
    monkeypatch.setattr(fundamentals, "FUNDAMENTALS_FILE", tmp_path / "fundamentals.csv")
    monkeypatch.setattr(macro, "USD_FILE", tmp_path / "usdtry.csv")
    monkeypatch.setattr(macro, "CPI_LOCAL", tmp_path / "cpi_local.csv")
    monkeypatch.setattr(macro, "SECOND_FILE", tmp_path / "usd_second_source.json")
    monkeypatch.setattr(macro, "_second_fetch", offline)
    monkeypatch.setattr(macro, "_http_get", offline)
    monkeypatch.setattr(levels_module, "_log_file", lambda: tmp_path / "levels_log.csv")
    # every signal_log write that does not name its file (e.g. /tara through the bot) stays private
    monkeypatch.setattr(signals_log, "SIGNAL_LOG_FILE", tmp_path / "signal_log.csv")
    monkeypatch.setattr(forward, "SIGNAL_LOG_FILE", tmp_path / "signal_log.csv")  # daily and elimination records
    monkeypatch.setattr(screen.C, "CACHE_FILE", tmp_path / "screen_cards.json")
    monkeypatch.setattr(screen.C, "TRIALS_FILE", tmp_path / "screen_trials.csv")
    screen.C._MEMORY.clear()
    screen.C._SESSIONS.clear()

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
