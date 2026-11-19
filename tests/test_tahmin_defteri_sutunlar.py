"""#12: prediction ledger columns (probability, reference close, assumptions, rule id) and the marking extras
(direction, always-up reference, TL / USD / XU100-relative returns). Synthetic data only; the tracked ledger is
never written."""

import csv
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path

import pandas as pd

from core.research import tahmin_defteri as td

OLD_COLUMNS = (
    "id", "tarih", "kayit_turu", "kaynak", "kaynak_puani_11", "varlik", "sembol", "fiyat", "fiyat_saati",
    "metin_tetik", "metin_hedef", "metin_gecersizlik", "yon", "tetik_turu", "tetik_seviye", "hedef_seviye",
    "gecersizlik_seviye", "son_tarih", "son_tarih_kaynagi", "isaretleme", "sonuc", "sonuc_tarihi",
    "al_etiketi", "sat_etiketi", "not",
)
NEW_COLUMNS = ("olasilik", "referans_fiyat", "varsayim_alanlari", "cozum_kurali", "yon_dogru", "hep_boga",
               "getiri_tl", "getiri_usd", "getiri_xu100_goreli")


def row(**kw):
    base = {c: "" for c in td.COLUMNS}
    base.update(id="X-1", tarih="2026-11-19", kayit_turu="tahmin", kaynak="k", kaynak_puani_11="7", varlik="AAA",
                sembol="AAA", yon="yukari", tetik_turu="kapanis_ustu", tetik_seviye="350", hedef_seviye="360",
                son_tarih="2026-12-03", isaretleme="otomatik", cozum_kurali="K-110")
    base.update(kw)
    return base


def series(*values, start="2026-11-19"):
    return pd.Series(values, index=pd.bdate_range(start, periods=len(values)), dtype=float)


# 19.11 .. 03.12 is 11 business days: publication close 348, deadline close 355
ASELS = series(348, 349, 352, 361, *[355] * 7)
BENCH = series(*[10000] * 10, 10100)
USD = pd.Series([40.0, 41.0], index=pd.to_datetime(["2026-11-19", "2026-12-03"]))


class ColumnsTest(unittest.TestCase):
    def test_old_columns_kept_in_order_new_ones_appended(self):
        self.assertEqual(td.COLUMNS, OLD_COLUMNS + NEW_COLUMNS)
        self.assertEqual(td.RESULT_COLUMNS[:4], ("id", "sonuc", "sonuc_tarihi", "isaretlendi"))
        for c in ("referans_fiyat", "yon_dogru", "hep_boga", "getiri_tl", "getiri_usd", "getiri_xu100_goreli"):
            self.assertIn(c, td.RESULT_COLUMNS)

    def test_probability_in_five_point_steps(self):
        for good in ("", "65", "0", "100", "%40"):
            td.check(row(olasilik=good))
        for bad in ("62", "105", "-5", "abc", "0.65"):
            with self.assertRaises(ValueError, msg=bad):
                td.check(row(olasilik=bad))

    def test_assumption_fields_must_be_columns(self):
        td.check(row(varsayim_alanlari="son_tarih,gecersizlik_seviye"))
        with self.assertRaises(ValueError):
            td.check(row(varsayim_alanlari="son_tarih,uydurma"))

    def test_project_ledger_new_columns_filled_from_notes(self):
        with open(td.LEDGER, encoding="utf-8", newline="") as f:
            header = next(csv.reader(f))
        self.assertEqual(tuple(header), td.COLUMNS)
        rows = {r["id"]: r for r in td.read(td.LEDGER)}
        self.assertEqual({r["cozum_kurali"] for r in rows.values()}, {"K-110"})
        self.assertEqual(rows["T-20261119-1"]["varsayim_alanlari"], "son_tarih")
        self.assertIn("gecersizlik_seviye", rows["T-20261119-6"]["varsayim_alanlari"].split(","))
        self.assertEqual(rows["T-20261119-3"]["varsayim_alanlari"], "")  # the source gave "1-2 hafta"
        for r in rows.values():  # filled at marking only, never in the tracked ledger
            for c in ("referans_fiyat", "yon_dogru", "hep_boga", "getiri_tl", "getiri_usd", "getiri_xu100_goreli"):
                self.assertEqual(r[c], "", (r["id"], c))


class ExtrasTest(unittest.TestCase):
    def test_up_row_direction_returns_and_relative(self):
        got = td.extras(row(), ASELS, BENCH, USD)
        self.assertEqual(got["referans_fiyat"], "348.00")
        self.assertEqual((got["yon_dogru"], got["hep_boga"]), ("evet", "evet"))
        tl = 355 / 348 - 1
        self.assertAlmostEqual(float(got["getiri_tl"]), tl, places=4)
        self.assertAlmostEqual(float(got["getiri_usd"]), (1 + tl) * 40 / 41 - 1, places=4)
        self.assertAlmostEqual(float(got["getiri_xu100_goreli"]), tl - 0.01, places=4)

    def test_down_row_wrong_direction_is_separate_from_result(self):
        got = td.extras(row(yon="asagi", tetik_turu="hemen", tetik_seviye="", hedef_seviye="300"), ASELS)
        self.assertEqual((got["yon_dogru"], got["hep_boga"]), ("hayır", "evet"))

    def test_reference_written_in_ledger_wins(self):
        got = td.extras(row(referans_fiyat="340"), ASELS)
        self.assertEqual(got["referans_fiyat"], "340")
        self.assertAlmostEqual(float(got["getiri_tl"]), 355 / 340 - 1, places=4)

    def test_missing_data_leaves_fields_empty(self):
        got = td.extras(row(), ASELS, None, None)
        self.assertEqual((got["getiri_usd"], got["getiri_xu100_goreli"]), ("", ""))
        short = td.extras(row(), ASELS.iloc[:5])  # the store does not reach the deadline
        self.assertEqual((short["yon_dogru"], short["hep_boga"], short["getiri_tl"]), ("", "", ""))
        no_ref = td.extras(row(), ASELS.iloc[1:])  # no close on or before the publication day
        self.assertEqual((no_ref["referans_fiyat"], no_ref["yon_dogru"]), ("", ""))


class DailyExtrasTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.ledger = self.dir / "TAHMIN_DEFTERI.csv"
        shutil.copy(td.LEDGER, self.ledger)
        self.results = self.dir / "tahmin_sonuclari.csv"

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def closes_for(self, symbol):
        return BENCH if symbol == "XU100.IS" else ASELS

    def test_extras_go_to_results_file_not_ledger(self):
        before = self.ledger.read_bytes()
        td.daily(date(2026, 12, 4), ledger=self.ledger, results=self.results, closes_for=self.closes_for, usd=USD)
        self.assertEqual(self.ledger.read_bytes(), before)
        rows = {r["id"]: r for r in td.read_with_results(self.ledger, self.results)}
        r = rows["T-20261119-1"]
        self.assertEqual((r["sonuc"], r["referans_fiyat"], r["yon_dogru"], r["hep_boga"]),
                         ("tuttu", "348.00", "evet", "evet"))
        self.assertNotEqual(r["getiri_usd"], "")

    def test_old_results_file_without_new_columns_is_read_and_extended(self):
        with open(self.results, "w", encoding="utf-8", newline="") as f:
            f.write("id,sonuc,sonuc_tarihi,isaretlendi\nT-ESKI,tutmadi,2026-11-30,2026-12-01\n")
        rows = td.read_with_results(self.ledger, self.results)
        self.assertEqual(len(rows), 7)
        td.daily(date(2026, 12, 4), ledger=self.ledger, results=self.results, closes_for=self.closes_for, usd=USD)
        with open(self.results, encoding="utf-8", newline="") as f:
            got = list(csv.DictReader(f))
        self.assertEqual(tuple(got[0].keys()), td.RESULT_COLUMNS)
        self.assertEqual((got[0]["id"], got[0]["sonuc"], got[0]["yon_dogru"]), ("T-ESKI", "tutmadi", ""))
        self.assertEqual(got[1]["id"], "T-20261119-1")


class ScorecardExtrasTest(unittest.TestCase):
    def test_brier_needs_twenty(self):
        rows = [row(id=str(i), olasilik="80", sonuc="tuttu" if i < 10 else "tutmadi") for i in range(19)]
        self.assertEqual(td.scorecard(rows)[0].brier(), "yetersiz örnek (N=19)")
        rows.append(row(id="19", olasilik="80", sonuc="tutmadi"))
        rows.append(row(id="x", olasilik="", sonuc="tuttu"))  # no probability: not counted
        self.assertEqual(td.scorecard(rows)[0].brier(), "0,340 (N=20)")

    def test_always_up_comparison_counts(self):
        rows = [row(id="1", yon_dogru="evet", hep_boga="evet"), row(id="2", yon_dogru="hayır", hep_boga="evet"),
                row(id="3", yon_dogru="evet", hep_boga="hayır"), row(id="4")]
        card = td.scorecard(rows)[0]
        self.assertEqual((card.yon_dogru, card.hep_boga, card.yon_n), (2, 2, 3))


if __name__ == "__main__":
    unittest.main()
