"""K-93 (3) and (7): the weekly SLO series table, the two-source streak and the 'records missing' note."""

import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from core.market.calendar import ISTANBUL
from core.reports import weekly_series as ws
from core.reports.health import OK, UNKNOWN, WARN
from core.reports.slo import TARGETS, SloResult


def results(accuracy=OK, others=OK):
    return [SloResult(name, accuracy if name == "Veri doğruluğu" else others, 1.0, "metin") for name in TARGETS]


def sat(day):
    return datetime(2026, 11, day, 21, 0, tzinfo=ISTANBUL) if day <= 30 else \
        datetime(2026, 12, day - 30, 21, 0, tzinfo=ISTANBUL)


class SeriesTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.path = self.dir / "seri.csv"
        self.beats = self.dir / "heartbeats.csv"
        self.beats.write_text("at,pid\n2026-11-03T15:14:32+03:00,1\n", encoding="utf-8")

    def add(self, day, **kw):
        return ws.record(sat(day), results(**kw), self.beats, self.path)

    def test_row_per_week_and_rerun_replaces(self):
        self.add(14)
        self.add(14, accuracy=WARN)
        rows = ws.read(self.path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Veri doğruluğu"], WARN)
        self.assertEqual(rows[0]["hafta"], "2026-11-14")

    def test_two_source_needs_four_consecutive_weeks(self):
        for d in (14, 21, 28):
            self.add(d)
        weeks, holds, text = ws.two_source(ws.read(self.path))
        self.assertEqual((weeks, holds), (3, False))
        self.assertIn("3/4", text)
        self.add(35)  # 05.12
        weeks, holds, text = ws.two_source(ws.read(self.path))
        self.assertEqual((weeks, holds), (4, True))
        self.assertIn("tutuyor", text)

    def test_unknown_or_warning_resets_the_streak(self):
        self.add(14)
        self.add(21, accuracy=UNKNOWN)
        self.add(28)
        self.assertEqual(ws.two_source(ws.read(self.path))[0], 1)
        self.add(35, accuracy=WARN)
        self.assertEqual(ws.two_source(ws.read(self.path))[0], 0)

    def test_slo_streak_counts_all_seven(self):
        self.add(14)
        self.add(21, others=WARN)
        self.add(28)
        self.assertEqual(ws.slo_streak(ws.read(self.path)), 1)

    def test_late_records_are_marked(self):
        # the 03.11 move: heartbeats start 03.11 15:14, the window of the 07.11 measurement begins 31.10 21:00
        row = ws.record(datetime(2026, 11, 7, 21, 0, tzinfo=ISTANBUL), results(), self.beats, self.path)
        self.assertIn("kayıt eksik", row["not"])
        self.assertEqual(row["kayit_basi"], "2026-11-03T15:14:32+03:00")
        self.assertEqual(ws.slo_streak(ws.read(self.path)), 0)  # a week with missing records never counts
        row = self.add(14)
        self.assertEqual(row["not"], "")

    def test_missing_heartbeats_file(self):
        self.beats.unlink()
        row = self.add(14)
        self.assertIn("kayıt eksik", row["not"])

    def test_text_for_the_saturday_summary(self):
        for d in (14, 21):
            self.add(d)
        text = ws.summary_lines(ws.read(self.path))
        self.assertTrue(any("SLO serisi: 2/4" in t for t in text))
        self.assertTrue(any("İki kaynak" in t for t in text))


SAVED_1411 = """🤖 Otonom günlük özet (14.11.2026) — yalnız bilgi
Haftalık SLO tablosu:
📐 SLO (son 7 gün): 6/7 hedefte, 1 ölçülemiyor
  ✅ Rapor teslimi: %100.0 (hedef ≥ %99 seans 19:00'a kadar) · 5/5 seans zamanında
  ✅ Bot ayakta kalma: %99.0 (hedef ≥ %98) · son sinyal 14.11 20:59
  ✅ Veri tazeliği: %100.0 (hedef ≥ %98 hisse 19:00'da güncel) · 5/5 seans
  ✅ Veri doğruluğu: %99.5 (hedef ≤ %1 hisse ikinci kaynaktan farklı) · 14.11: 1/206 hisse farklı (kaynak: Borsa İstanbul resmî gün sonu) (RALYH)
  ✅ Yedek: %100.0 (hedef her gün + haftalık geri yükleme testi) · 5/5 seans günü yedekli
  ✅ Kayıt bütünlüğü: — (hedef 0 bozuk / tekrar / eksik) · sorun yok
  ❔ Kalite (CI, kapsam): — (hedef CI yeşil, kapsam ≥ %90) · GitHub sorgulanamadı (ConnectError); son bilinen (14.11 13:55)
"""


class Response:
    def __init__(self, runs):
        self.runs = runs

    def raise_for_status(self):
        return None

    def json(self):
        return {"workflow_runs": self.runs}


def run(i, started, conclusion="success"):
    return {"id": i, "run_started_at": started, "status": "completed", "conclusion": conclusion,
            "head_sha": f"{i:040d}"}


class BackfillAndK92Test(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        (self.dir / "2026-11-14.txt").write_text(SAVED_1411, encoding="utf-8")
        self.path = self.dir / "seri.csv"
        self.beats = self.dir / "heartbeats.csv"
        self.beats.write_text("at,pid\n2026-11-03T15:14:32+03:00,1\n", encoding="utf-8")

    def test_saved_saturday_tables_are_backfilled_with_k92(self):
        runs = [run(2, "2026-11-14T20:29:44Z"), run(1, "2026-11-14T10:55:27Z")]  # 2 started after 21:00 (+03)
        added = ws.backfill(self.dir, self.beats, self.path, get=lambda url, **kw: Response(runs))
        self.assertEqual(added, ["2026-11-14"])
        row = ws.read(self.path)[0]
        self.assertEqual(row["Veri doğruluğu"], OK)
        self.assertEqual(row["dogruluk_degeri"], "0.9950")
        self.assertEqual(row["Kalite (CI, kapsam)"], OK)
        self.assertIn("K-92 yeniden sorgu: 1", row["not_k92"])
        self.assertEqual(ws.slo_streak(ws.read(self.path)), 1)
        self.assertEqual(ws.backfill(self.dir, self.beats, self.path, get=lambda url, **kw: Response(runs)), [])

    def test_k92_red_or_unreachable_stays_unknown(self):
        ws.backfill(self.dir, self.beats, self.path,
                    get=lambda url, **kw: Response([run(1, "2026-11-14T10:55:27Z", "failure")]))
        self.assertEqual(ws.read(self.path)[0]["Kalite (CI, kapsam)"], UNKNOWN)
        self.path.unlink()

        def offline(url, **kw):
            raise OSError("ağ yok")

        ws.backfill(self.dir, self.beats, self.path, get=offline)
        self.assertEqual(ws.read(self.path)[0]["Kalite (CI, kapsam)"], UNKNOWN)
        self.assertEqual(ws.slo_streak(ws.read(self.path)), 0)

    def test_k92_never_applies_to_a_spent_quota(self):
        r = SloResult("Kalite (CI, kapsam)", UNKNOWN, None, "GitHub sorgulanamadı (HTTP 403, GitHub kotası doldu)")
        self.assertFalse(ws.network_error(r))
        r = SloResult("Kalite (CI, kapsam)", UNKNOWN, None, "GitHub sorgulanamadı (HTTP 404)")
        self.assertFalse(ws.network_error(r))
        for text in ("GitHub sorgulanamadı (ConnectError)", "GitHub sorgulanamadı (HTTP 503)"):
            self.assertTrue(ws.network_error(SloResult("Kalite (CI, kapsam)", UNKNOWN, None, text)))


if __name__ == "__main__":
    unittest.main()
