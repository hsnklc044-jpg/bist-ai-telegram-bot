"""Prediction ledger marking rules (K-110) and market note template, synthetic data only."""

import unittest
from datetime import date
from pathlib import Path

import pandas as pd

from core.reports import piyasa_notu as pn
from core.research import tahmin_defteri as td


def row(**kw):
    base = {c: "" for c in td.COLUMNS}
    base.update(id="X-1", tarih="2026-11-19", kayit_turu="tahmin", kaynak="k", kaynak_puani_11="7", varlik="AAA",
                sembol="AAA", yon="yukari", tetik_turu="kapanis_ustu", tetik_seviye="350", hedef_seviye="360",
                son_tarih="2026-11-25", isaretleme="otomatik")
    base.update(kw)
    return base


def closes(*values, start="2026-11-20"):
    return pd.Series(values, index=pd.bdate_range(start, periods=len(values)), dtype=float)


AFTER = date(2026, 11, 26)


class MarkingRuleTest(unittest.TestCase):
    def test_trigger_then_target_is_a_hit(self):
        self.assertEqual(td.evaluate(row(), closes(349, 351, 355, 360), AFTER), ("tuttu", "2026-11-25"))

    def test_intraday_does_not_count_only_closes(self):
        # closes stay at or under the trigger: a close equal to 350 is not "above"
        self.assertEqual(td.evaluate(row(), closes(350, 350, 349, 348), AFTER)[0], "tetiklenmedi")

    def test_trigger_day_can_also_reach_the_target(self):
        self.assertEqual(td.evaluate(row(), closes(361), AFTER), ("tuttu", "2026-11-20"))

    def test_triggered_but_target_missed(self):
        self.assertEqual(td.evaluate(row(), closes(351, 355, 359), AFTER), ("tutmadi", "2026-11-25"))

    def test_invalidation_first_is_a_miss_even_before_trigger(self):
        r = row(gecersizlik_seviye="340")
        self.assertEqual(td.evaluate(r, closes(345, 339, 365), AFTER), ("tutmadi", "2026-11-23"))

    def test_invalidation_checked_before_target_same_day_down(self):
        r = row(yon="asagi", tetik_turu="hemen", tetik_seviye="", hedef_seviye="100", gecersizlik_seviye="120")
        self.assertEqual(td.evaluate(r, closes(110, 121, 99), AFTER), ("tutmadi", "2026-11-23"))
        self.assertEqual(td.evaluate(r, closes(110, 100), AFTER), ("tuttu", "2026-11-23"))

    def test_close_on_start_day_and_after_deadline_ignored(self):
        s = pd.Series([400.0, 349.0, 500.0],
                      index=pd.to_datetime(["2026-11-19", "2026-11-20", "2026-11-26"]))
        self.assertEqual(td.evaluate(row(), s, date(2026, 11, 27))[0], "tetiklenmedi")

    def test_not_due_and_manual_rows_untouched(self):
        self.assertIsNone(td.evaluate(row(), closes(361), date(2026, 11, 25)))
        self.assertIsNone(td.evaluate(row(isaretleme="elle"), closes(361), AFTER))
        self.assertIsNone(td.evaluate(row(sonuc="tuttu"), closes(300), AFTER))

    def test_no_data_is_unmeasurable(self):
        self.assertEqual(td.evaluate(row(), pd.Series(dtype=float), AFTER)[0], "olculemez")

    def test_bad_rows_refused(self):
        with self.assertRaises(ValueError):
            td.check(row(gecersizlik_seviye="365"))  # invalidation beyond the target for an up scenario
        with self.assertRaises(ValueError):
            td.check(row(tetik_turu="elle"))
        with self.assertRaises(ValueError):
            td.check(row(sonuc="belki"))

    def test_mark_changes_only_due_rows(self):
        rows = [row(id="a"), row(id="b", son_tarih="2026-12-30"), row(id="c", isaretleme="elle")]
        changed = td.mark(rows, lambda s: closes(361), AFTER)
        self.assertEqual(changed, ["a"])
        self.assertEqual(rows[0]["sonuc"], "tuttu")
        self.assertEqual(rows[1]["sonuc"], "")


class ScorecardTest(unittest.TestCase):
    def test_small_sample_shows_no_rate(self):
        rows = [row(id=str(i), sonuc="tuttu") for i in range(9)]
        card = td.scorecard(rows)[0]
        self.assertEqual(card.isabet(), "yetersiz örnek (N=9)")

    def test_rate_from_ten(self):
        rows = [row(id=str(i), sonuc="tuttu" if i < 6 else "tutmadi") for i in range(10)]
        rows.append(row(id="t", sonuc="tetiklenmedi"))
        card = td.scorecard(rows)[0]
        self.assertEqual((card.n, card.tetiklenmedi, card.isabet()), (10, 1, "%60 (N=10)"))

    def test_direction_changes_counted_per_asset(self):
        rows = [row(id="1", tarih="2026-11-01", yon="yukari"), row(id="2", tarih="2026-11-03", yon="asagi"),
                row(id="3", tarih="2026-11-05", yon="yukari"), row(id="4", varlik="BBB", yon="asagi")]
        self.assertEqual(td.scorecard(rows)[0].yon_degisimi, 2)

    def test_mean_score_skips_blank(self):
        rows = [row(id="1", kaynak_puani_11="11"), row(id="2", kaynak_puani_11="6"), row(id="3", kaynak_puani_11="")]
        self.assertAlmostEqual(td.scorecard(rows)[0].ortalama_puan, 8.5)


class LedgerFileTest(unittest.TestCase):
    def test_project_ledger_is_valid_and_round_trips(self):
        rows = td.read(td.LEDGER)
        self.assertEqual(len(rows), 7)
        self.assertEqual([r["id"] for r in rows], [f"T-20261119-{i}" for i in range(1, 8)])
        auto = [r["id"] for r in rows if r["isaretleme"] == "otomatik"]
        self.assertEqual(auto, ["T-20261119-1"])
        tmp = Path(self.id().split(".")[-1] + ".csv")
        try:
            td.write(rows, tmp)
            self.assertEqual(td.read(tmp), rows)
        finally:
            tmp.unlink(missing_ok=True)


def note(**kw):
    base = dict(varlik="AAA", fiyat=348.0, fiyat_zamani="2026-11-19 18:10 (günlük kapanış)", sure="Günlük, 10 işlem günü",
                konum_tl="200 günlük ortalamanın altında", konum_usd=None, bekleme_bolgesi="345–350",
                teyit="350 üstü günlük kapanış", hedefler="360 / 365–370", gecersizlik=340.0, gecersizlik_yonu="altı",
                hedef_atr=0.8, gecmis_oran=None, ozet="Senaryo 350 üstü kapanışla başlar.")
    base.update(kw)
    return pn.Note(**base)


class MarketNoteTest(unittest.TestCase):
    def test_all_fields_written_and_missing_ones_named(self):
        text = pn.render(note())
        for part in ("Fiyat: 348.00 (2026-11-19 18:10", "Konum (USD): veri yok", "Geçmiş oran: henüz ölçülmedi",
                     "0.8 ATR (1'in altı: gürültü)", "Geçersizlik: 340.00 altı günlük kapanış", pn.WARNING):
            self.assertIn(part, text)

    def test_banned_words_refused_but_not_inside_words(self):
        with self.assertRaises(ValueError):
            pn.render(note(ozet="Güçlü kırılımda al."))
        with self.assertRaises(ValueError):
            pn.render(note(teyit="kalıcı kırılım"))
        self.assertEqual(pn.problems("satır alt salı alan"), [])

    def test_price_needs_time_and_summary_one_sentence(self):
        with self.assertRaises(ValueError):
            pn.render(note(fiyat_zamani=""))
        with self.assertRaises(ValueError):
            pn.render(note(ozet="Bir. İki."))


if __name__ == "__main__":
    unittest.main()
