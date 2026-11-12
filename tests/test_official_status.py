"""Ö39 (öz-denetim 10, 12.11.2026): a failed official import or a refused file shows in /durum, not only in the log."""

import asyncio
import json
from datetime import datetime
from types import SimpleNamespace

from core.official import compare, indices, prices, status
from core.reports import health

NOW = datetime(2026, 11, 13, 9, 0)


def _run_job(monkeypatch, tmp_path, importer):
    from bot import scheduler

    monkeypatch.setattr(status, "STATE_FILE", tmp_path / "official_import.json")
    monkeypatch.setattr(prices, "import_folder", importer)
    monkeypatch.setattr(indices, "import_folder", lambda: prices.ImportResult())
    monkeypatch.setattr(compare, "yahoo_check", lambda now: None)
    monkeypatch.setattr(compare, "yahoo_index_check", lambda now: None)
    asyncio.run(scheduler.official_prices_job(SimpleNamespace(job=None, bot=None)))
    return tmp_path / "official_import.json"


def test_a_failed_import_is_recorded_and_shown(monkeypatch, tmp_path):
    def boom():
        raise OSError("disk dolu")

    state = _run_job(monkeypatch, tmp_path, boom)

    assert "disk dolu" in json.loads(state.read_text(encoding="utf-8"))["error"]
    check = health.official_check(state)
    assert check.state == health.WARN
    assert "başarısız" in check.text and "disk dolu" in check.text


def test_a_refused_file_is_shown_until_a_later_read(monkeypatch, tmp_path):
    refused = prices.ImportResult(files=2, rows=5, rejected=["PP_X.csv: bilinmeyen başlık"])
    state = _run_job(monkeypatch, tmp_path, lambda: refused)
    check = health.official_check(state)
    assert check.state == health.WARN
    assert "PP_X.csv" in check.text

    _run_job(monkeypatch, tmp_path, lambda: prices.ImportResult())  # a quiet night keeps the last read
    assert health.official_check(state).state == health.WARN

    _run_job(monkeypatch, tmp_path, lambda: prices.ImportResult(files=1, rows=9))
    check = health.official_check(state)
    assert check.state == health.OK
    assert "1 dosya" in check.text


def test_no_record_yet_is_only_information(tmp_path):
    assert health.official_check(tmp_path / "none.json").state == health.INFO


def test_the_check_is_in_durum():
    import inspect

    assert "official_check(" in inspect.getsource(health.health_checks)
