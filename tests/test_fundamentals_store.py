"""
Profesyonel filtreler, Aşama 3 (DECISIONS K-48): data/fundamentals.csv keeps every item with the
time it was PUBLISHED. A screen or a card on a given session sees only what was published before
that session (no look-ahead). Rows come in by a checked file import, never by network (KAP's
terms are not confirmed). Append-only, backed up, schema-checked, and shown in /durum.
"""

import tempfile
import unittest
from datetime import date
from pathlib import Path

import pandas as pd

from core.fundamentals import store

HEADER = "symbol,period_end,published_at,item,value,unit,consolidated,inflation_adjusted,source\n"


def row(symbol="THYAO", period="2025-12-31", published="2026-03-05T18:30:00+03:00", item="net_income",
        value="100", unit="TL", consolidated="1", inflation="1", source="https://www.kap.org.tr/tr/Bildirim/1"):
    return f"{symbol},{period},{published},{item},{value},{unit},{consolidated},{inflation},{source}\n"


class Files(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.path = self.dir / "fundamentals.csv"

    def source(self, *rows, name="in.csv"):
        path = self.dir / name
        path.write_text(HEADER + "".join(rows), encoding="utf-8")
        return path


class ImportTest(Files):
    def test_valid_rows_are_appended_once(self):
        added, rejected = store.import_file(self.source(row(), row(item="revenue", value="900")), self.path)
        self.assertEqual((added, rejected), (2, []))
        again, _ = store.import_file(self.source(row()), self.path)
        self.assertEqual(again, 0)  # the same fact is not written twice
        self.assertEqual(len(store.load(self.path)), 2)

    def test_bad_rows_are_named_and_skipped(self):
        bad = [
            row(published="2025-12-30T10:00:00+03:00"),  # published before the period ended
            row(item="tahmin"),  # not a known item
            row(value="yüz"),
            row(source=""),
            row(symbol="THY AO"),
            row(period="31.12.2025"),
            row(consolidated="evet"),
        ]
        added, rejected = store.import_file(self.source(*bad), self.path)
        self.assertEqual(added, 0)
        self.assertEqual(len(rejected), len(bad))
        text = " ".join(rejected)
        for word in ("yayın tarihi", "bilinmeyen kalem", "sayı", "kaynak", "kod", "tarih", "konsolide"):
            self.assertIn(word, text)

    def test_append_only(self):
        store.import_file(self.source(row()), self.path)
        before = self.path.read_text(encoding="utf-8")
        store.import_file(self.source(row(item="revenue")), self.path)
        self.assertTrue(self.path.read_text(encoding="utf-8").startswith(before))

    def test_no_network(self):
        source = Path(store.__file__).read_text(encoding="utf-8")
        for word in ("requests", "urllib", "http.client", "httpx"):
            self.assertNotIn(word, source)


class PointInTimeTest(Files):
    def setUp(self):
        super().setUp()
        store.import_file(self.source(
            row(period="2025-09-30", published="2025-11-10T18:00:00+03:00", value="50"),
            row(period="2025-12-31", published="2026-03-05T18:30:00+03:00", value="100"),
            row(period="2025-12-31", published="2026-04-01T09:00:00+03:00", value="90"),  # a restatement
        ), self.path)
        self.data = store.load(self.path)

    def test_only_what_was_published_before_the_session(self):
        value = lambda day: store.as_of(self.data, "THYAO", "net_income", day)  # noqa: E731
        self.assertIsNone(value(date(2025, 11, 10)))  # published that evening: not usable that session
        self.assertEqual(value(date(2025, 11, 11)), 50)
        self.assertEqual(value(date(2026, 3, 5)), 50)
        self.assertEqual(value(date(2026, 3, 6)), 100)
        self.assertEqual(value(date(2026, 4, 2)), 90)  # the newest publication of the newest period
        self.assertIsNone(store.as_of(self.data, "GARAN", "net_income", date(2026, 4, 2)))

    def test_panel_for_the_card(self):
        index = pd.bdate_range("2025-11-07", "2026-04-03")
        panel = store.panel(self.data, "net_income", ["THYAO", "GARAN"], index)
        self.assertTrue(pd.isna(panel.loc["2025-11-10", "THYAO"]))
        self.assertEqual(panel.loc["2025-11-11", "THYAO"], 50)
        self.assertEqual(panel.loc["2026-03-06", "THYAO"], 100)
        self.assertEqual(panel.loc["2026-04-02", "THYAO"], 90)
        self.assertTrue(panel["GARAN"].isna().all())

    def test_inflation_adjusted_rows_are_marked(self):
        self.assertEqual(set(self.data["inflation_adjusted"]), {"1"})
        self.assertIn("inflation_adjusted", store.COLUMNS)


class CoverageAndCompareTest(Files):
    def test_coverage_and_status_line(self):
        self.assertIn("veri yok", store.status_text(self.path, ["THYAO.IS", "GARAN.IS"]))
        rows = [row(item=item) for item in store.CORE_ITEMS]
        rows += [row(symbol="GARAN", item="net_income")]
        store.import_file(self.source(*rows), self.path)
        text = store.status_text(self.path, ["THYAO.IS", "GARAN.IS"])
        self.assertIn("2 hisseden 1'inde eksiksiz", text)
        self.assertIn("05.03.2026", text)

    def test_second_source_comparison(self):
        store.import_file(self.source(row(value="100"), row(item="revenue", value="900")), self.path)
        other = self.source(row(value="103"), row(item="revenue", value="900"), name="other.csv")
        report = store.compare(self.path, other)
        self.assertIn("net_income", report)
        self.assertIn("%3,0", report)
        self.assertIn("1 kalem aynı", report)


class CommandLineTest(Files):
    def test_import_compare_status(self):
        import io
        from contextlib import redirect_stdout
        from unittest import mock

        with mock.patch.object(store, "FUNDAMENTALS_FILE", self.path), redirect_stdout(io.StringIO()) as out:
            self.assertEqual(store.main(["--import", str(self.source(row()))]), 0)
            self.assertEqual(store.main(["--import", str(self.source(row(item="x"), name="bad.csv"))]), 1)
            store.main(["--compare", str(self.source(row(), name="other.csv"))])
            store.main(["--status"])
        text = out.getvalue()
        self.assertIn("1 satır eklendi", text)
        self.assertIn("bilinmeyen kalem", text)
        self.assertIn("1 kalem aynı", text)
        self.assertIn("son yayın 05.03.2026", text)


class WiringTest(unittest.TestCase):
    def test_backup_schema_gitignore_and_status(self):
        from core import backup
        from core.config.paths import FUNDAMENTALS_FILE, ROOT_DIR
        from core.reports import health

        self.assertIn(FUNDAMENTALS_FILE, backup.PERSONAL_FILES)
        self.assertIn(FUNDAMENTALS_FILE, health.SCHEMAS)
        self.assertIn("data/fundamentals.csv", (ROOT_DIR / ".gitignore").read_text(encoding="utf-8"))
        names = [c.name for c in health.health_checks()]
        self.assertIn("Temel veri", names)


if __name__ == "__main__":
    unittest.main()
