"""Getting ready to change the price source (J madde 4, the user's 11.11.2026 decision). Written before the code.

Every stored price row keeps its source; one source interface for prices and fundamentals; a licensed source
connects once its key is in .env, and its first job is a comparison against the old data, which reopens the
second-source check of the "Veri doğruluğu" objective."""

import json
import sqlite3
import unittest
from datetime import date, datetime

import pandas as pd
import pytest

from core.market import provider, second_source, sources, store, trust
from core.market.calendar import ISTANBUL

NOW = datetime(2026, 11, 11, 19, 0, tzinfo=ISTANBUL)


def frame(days, close=10.0):
    idx = pd.to_datetime(days)
    return pd.DataFrame({"open": close, "high": close, "low": close, "close": close, "volume": 1000.0}, index=idx)


def series_frame():
    days = pd.bdate_range("2026-09-15", "2026-11-10")
    close = pd.Series([10.0 + (i % 5) * 0.1 for i in range(len(days))], index=days)
    return pd.DataFrame({"open": close, "high": close, "low": close, "close": close, "volume": 1000.0})


class FakeProvider:
    def __init__(self, name, frames):
        self.name = name
        self.frames = frames

    def fetch(self, symbols, start):
        return {s: self.frames[s] for s in symbols if s in self.frames}


@pytest.fixture(autouse=True)
def _env(tmp_path, monkeypatch):
    monkeypatch.delenv("QUANTBIST_PRICE_SOURCE", raising=False)
    monkeypatch.delenv("QUANTBIST_PRICE_SOURCE_KEY", raising=False)
    monkeypatch.setattr(second_source, "SUMMARY_FILE", tmp_path / "price_second_source.json")
    monkeypatch.setattr(sources, "STATE_DIR", tmp_path)
    monkeypatch.setattr(sources, "REGISTRY", {})
    previous = provider.get_provider()
    yield
    provider.set_provider(previous)


class StoreSourceTest(unittest.TestCase):
    def test_every_written_row_keeps_its_source(self):
        provider.set_provider(FakeProvider("yahoo", {"AAA.IS": frame(["2026-11-09", "2026-11-10"])}))
        store.update(["AAA.IS"], force=True, now=NOW)
        got = store.read_sources("AAA.IS")
        self.assertEqual(list(got), ["yahoo", "yahoo"])
        self.assertEqual(store.source_of("AAA.IS", date(2026, 11, 10)), "yahoo")

    def test_rows_stored_before_this_version_count_as_yahoo(self):
        store.read("AAA.IS")  # creates the schema
        with sqlite3.connect(store._db_path) as conn:  # an older version's positional insert still works
            conn.execute("INSERT OR REPLACE INTO prices VALUES (?, ?, ?, ?, ?, ?, ?)",
                         ("AAA.IS", "2026-11-05", 1, 1, 1, 1, 1))
        self.assertEqual(store.source_of("AAA.IS", date(2026, 11, 5)), "yahoo")
        self.assertEqual(list(store.read("AAA.IS").columns), ["open", "high", "low", "close", "volume"])

    def test_a_full_rewrite_replaces_the_sources_too(self):
        provider.set_provider(FakeProvider("yahoo", {"AAA.IS": frame(["2026-11-09", "2026-11-10"])}))
        store.update(["AAA.IS"], force=True, now=NOW)
        provider.set_provider(FakeProvider("lisansli", {"AAA.IS": frame(["2026-11-10"])}))
        store.update(["AAA.IS"], force=True, now=NOW)
        self.assertEqual(store.read_sources("AAA.IS").to_dict(), {pd.Timestamp("2026-11-10"): "lisansli"})


class LicensedSource:
    name = "deneme_dagitici"
    level = 1
    origin = "deneme dağıtıcı"
    terms_doc = "docs/DATA_SOURCES.md"  # an adapter is written only after its terms are recorded there

    def __init__(self, key):
        self.key = key

    def fetch(self, symbols, start):
        return {s: series_frame() for s in symbols}


class InterfaceTest(unittest.TestCase):
    def test_nothing_connects_without_a_name_an_adapter_and_a_key(self, ):
        env = {}
        self.assertIsNone(sources.configured(env))
        env["QUANTBIST_PRICE_SOURCE"] = "deneme_dagitici"
        self.assertIsNone(sources.configured(env))  # no adapter written for it
        sources.REGISTRY["deneme_dagitici"] = LicensedSource
        self.assertIsNone(sources.configured(env))  # no key yet
        env["QUANTBIST_PRICE_SOURCE_KEY"] = "anahtar"
        got = sources.configured(env)
        self.assertIsInstance(got, LicensedSource)
        self.assertEqual(got.key, "anahtar")

    def test_yahoo_is_described_as_level_3(self):
        self.assertEqual(sources.YAHOO.level, 3)
        self.assertEqual(sources.YAHOO.name, "yahoo")
        self.assertEqual(sources.YAHOO.level, trust.Trust(3, "Yahoo").level)

    def test_the_interface_covers_prices_and_fundamentals(self):
        self.assertTrue(hasattr(sources, "PriceSource"))
        self.assertTrue(hasattr(sources, "FundamentalSource"))


class FirstConnectionTest(unittest.TestCase):
    def setUp(self):
        sources.REGISTRY["deneme_dagitici"] = LicensedSource
        self.env = {"QUANTBIST_PRICE_SOURCE": "deneme_dagitici", "QUANTBIST_PRICE_SOURCE_KEY": "anahtar"}

    def fake_bars(self, symbol):
        return series_frame()

    def test_the_first_job_is_a_comparison_that_reopens_the_second_source_check(self):
        text = sources.first_connection(NOW, codes=["AAA", "BBB"], env=self.env, bars=self.fake_bars)
        self.assertIn("deneme_dagitici", text)
        summary = json.loads(second_source.SUMMARY_FILE.read_text(encoding="utf-8"))
        self.assertEqual(summary["checked"], 2)
        self.assertEqual(summary["differing"], [])
        self.assertIn("deneme", summary["source"])
        self.assertTrue((sources.STATE_DIR / "kaynak_deneme_dagitici.json").exists())
        self.assertIsNone(sources.first_connection(NOW, codes=["AAA"], env=self.env, bars=self.fake_bars))  # once

    def test_nothing_happens_without_a_connected_source(self):
        self.assertIsNone(sources.first_connection(NOW, codes=["AAA"], env={}, bars=self.fake_bars))
        self.assertFalse(second_source.SUMMARY_FILE.exists())

    def test_the_key_never_reaches_the_report_or_the_state(self):
        sources.first_connection(NOW, codes=["AAA"], env=self.env, bars=self.fake_bars)
        for path in sources.STATE_DIR.iterdir():
            if path.is_file():
                self.assertNotIn("anahtar", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()


class WiringTest(unittest.TestCase):
    def test_the_evening_run_sends_the_first_comparison(self):
        import inspect

        from core.reports import daily

        self.assertIn("_first_source_connection(lambda text: send_telegram(", inspect.getsource(daily))
        self.assertIn("sources.first_connection(", inspect.getsource(daily._first_source_connection))

    def test_the_stop_flag_stays_out_of_git(self):
        from pathlib import Path

        self.assertIn("data/otonom_dur.flag", Path(".gitignore").read_text(encoding="utf-8"))
