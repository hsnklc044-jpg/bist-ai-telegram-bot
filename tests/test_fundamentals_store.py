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

    def test_a_unit_other_than_tl_and_a_turkish_number_are_rejected(self):
        added, rejected = store.import_file(
            self.source(row(unit="bin TL"), row(item="revenue", value='"1.234,5"'), row(item="sga", value="inf"),
                        row(item="cash", unit="tl")), self.path)
        self.assertEqual(added, 1)  # "tl" is TL
        text = " ".join(rejected)
        self.assertIn("1000 ile çarp", text)
        self.assertIn("binlik ayırıcı yok", text)
        self.assertIn("sonlu", text)
        self.assertEqual(set(store.load(self.path)["unit"]), {"TL"})

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


class DryRunAndTemplateTest(Files):
    def test_the_dry_run_writes_nothing_and_names_what_is_missing(self):
        store.import_file(self.source(row(item="revenue")), self.path)
        before = self.path.read_bytes()
        src = self.source(row(item="revenue"), row(item="net_income"), row(item="tahmin"),
                          row(symbol="GARAN", item="total_assets", consolidated="0"))
        text = store.check_file(src, self.path)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertIn("2 satır eklenecek, 1 satır zaten var, 1 satır reddedilecek", text)
        self.assertIn("satır 4: bilinmeyen kalem", text)
        self.assertIn("THYAO 2025-12-31 (konsolide): 1 kalem; eksik ana kalem: revenue, gross_profit", text)
        self.assertIn("GARAN 2025-12-31 (solo)", text)
        self.assertIn("3 satır eklenecek", store.check_file(src, self.dir / "missing.csv"))
        self.assertFalse((self.dir / "missing.csv").exists())  # a dry run on an empty store creates nothing

    def test_a_complete_report_is_said_and_a_missing_column_is_named(self):
        items = [row(item=i, value="1") for i in store.CORE_ITEMS]
        self.assertIn("9 ana kalemin hepsi var", store.check_file(self.source(*items), self.path))
        bad = self.dir / "bad.csv"
        bad.write_text("symbol,period_end,value\nTHYAO,2025-12-31,1\n", encoding="utf-8")
        self.assertIn("eksik sütun", store.check_file(bad, self.path))

    def test_the_template_has_every_core_item_and_is_rejected_until_filled(self):
        text = store.template(["thyao", "GARAN.IS"], "2026-09-30")
        lines = text.splitlines()
        self.assertEqual(lines[0], ",".join(store.SOURCE_COLUMNS))
        self.assertEqual(len(lines), 1 + 2 * len(store.CORE_ITEMS))
        self.assertTrue(lines[1].startswith("THYAO,2026-09-30,,revenue,,TL,1,1,"))
        sheet = self.dir / "sablon.csv"
        sheet.write_text(text, encoding="utf-8")
        added, rejected = store.import_file(sheet, self.path)
        self.assertEqual((added, len(rejected)), (0, 18))  # empty cells never enter the store
        for bad in ((["THY AO"], "2026-09-30"), (["THYAO"], "30.09.2026"), ([], "2026-09-30")):
            with self.assertRaises(ValueError):
                store.template(*bad)

    def test_the_command_line_does_not_overwrite_a_file(self):
        import contextlib
        import io

        target = self.dir / "t.csv"
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(store.main(["--template", str(target), "--symbols", "THYAO", "--period", "2026-09-30"]), 0)
            first = target.read_text(encoding="utf-8")
            self.assertEqual(store.main(["--template", str(target), "--symbols", "GARAN", "--period", "2026-09-30"]), 1)
            self.assertEqual(store.main(["--template", str(self.dir / "u.csv"), "--symbols", "THYAO",
                                         "--period", "x"]), 1)
        self.assertEqual(target.read_text(encoding="utf-8"), first)
        self.assertFalse((self.dir / "u.csv").exists())


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
