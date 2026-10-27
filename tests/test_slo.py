"""Service level objectives (docs/CHARTER.md §2): measured from local records, unknown when not measurable."""

import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

from core.market.calendar import ISTANBUL
from core.reports import slo
from core.reports.health import OK, UNKNOWN, WARN

NOW = datetime(2026, 11, 6, 21, 0, tzinfo=ISTANBUL)  # Friday; week 02.11-06.11 has no holiday
WEEK = [date(2026, 11, d) for d in range(2, 7)]


class Temp(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def runs(self, rows):
        path = self.dir / "runs.csv"
        path.write_text("started_at,finished_at,data_day,status,detail\n" + "".join(
            f"{d}T18:30:00+03:00,{d}T{t}+03:00,{d},{s},\n" for d, t, s in rows), encoding="utf-8")
        return path


class ReportDeliveryTest(Temp):
    def test_all_on_time(self):
        r = slo.report_delivery(NOW, self.runs([(d, "18:32:00", "sent") for d in WEEK]))
        self.assertEqual((r.state, r.value), (OK, 1.0))
        self.assertIn("5/5", r.text)

    def test_late_and_missing_days(self):
        rows = [(WEEK[0], "18:32:00", "sent"), (WEEK[1], "19:20:00", "sent"),  # after 19:00 = late
                (WEEK[3], "18:31:00", "sent"), (WEEK[4], "18:31:00", "sent")]  # 04.11 missing
        r = slo.report_delivery(NOW, self.runs(rows))
        self.assertEqual(r.state, WARN)
        self.assertAlmostEqual(r.value, 3 / 5)
        self.assertIn("geç: 03.11", r.text)
        self.assertIn("eksik: 04.11", r.text)

    def test_sending_twice_or_on_a_holiday_is_an_error(self):
        rows = [(d, "18:32:00", "sent") for d in WEEK] + [(WEEK[2], "18:40:00", "sent")]
        r = slo.report_delivery(NOW, self.runs(rows))
        self.assertEqual(r.state, WARN)
        self.assertIn("iki kez: 04.11", r.text)

    def test_today_before_19_is_not_counted_yet(self):
        morning = NOW.replace(hour=12)
        r = slo.report_delivery(morning, self.runs([(d, "18:32:00", "sent") for d in WEEK[:4]]))
        self.assertIn("4/4", r.text)

    def test_no_record_is_unknown(self):
        self.assertEqual(slo.report_delivery(NOW, self.dir / "yok.csv").state, UNKNOWN)


class MeasurementStartTest(Temp):
    """PC 27.10 16:19: runs.csv and dated backups began on 26.10, yet 21-23.10 were counted as missing.
    Days before the first record were not measured: they are left out, not counted as failures."""

    def test_report_delivery_starts_at_the_first_record(self):
        r = slo.report_delivery(NOW, self.runs([(d, "18:32:00", "sent") for d in WEEK[3:]]))
        self.assertEqual((r.state, r.value), (OK, 1.0))
        self.assertIn("2/2", r.text)
        self.assertIn("ölçüm 05.11'de başladı", r.text)

    def test_backups_start_at_the_first_backup(self):
        folder = self.dir / "yedek"
        folder.mkdir()
        for d in WEEK[3:]:
            (folder / f"quantbist_{d.isoformat()}.zip").write_bytes(b"x")
        restores = self.dir / "restore_tests.csv"
        slo.record_restore_test(True, "ok", path=restores, now=NOW - timedelta(days=1))
        r = slo.backup_slo(NOW, folder, restores)
        self.assertEqual(r.state, OK, r.text)
        self.assertIn("2/2", r.text)

    def test_freshness_starts_at_the_first_record(self):
        path = self.dir / "freshness.csv"
        d = WEEK[4]
        slo.record_freshness(d, 100, 100, xu100=True, path=path,
                             now=datetime.combine(d, datetime.min.time(), ISTANBUL).replace(hour=18, minute=35))
        r = slo.freshness(NOW, path)
        self.assertEqual((r.state, r.value), (OK, 1.0))


class BotUptimeTest(Temp):
    def log(self, beats):
        path = self.dir / "heartbeats.csv"
        path.write_text("at,pid\n" + "".join(f"{t.isoformat(timespec='seconds')},{p}\n" for t, p in beats),
                        encoding="utf-8")
        return path

    def test_every_five_minutes_is_full_uptime(self):
        start = NOW - timedelta(days=7)
        beats = [(start + timedelta(minutes=5 * i), 1) for i in range(7 * 24 * 12 + 1)]
        r = slo.bot_uptime(NOW, self.log(beats))
        self.assertEqual(r.state, OK)
        self.assertGreaterEqual(r.value, 0.99)

    def test_a_gap_with_the_same_process_is_sleep_shown_apart(self):
        start = NOW - timedelta(days=7)
        beats = [(start + timedelta(minutes=5 * i), 1) for i in range(7 * 24 * 12 + 1)
                 if not (1000 <= i < 1240)]  # 20 hours without a beat, same process before and after
        r = slo.bot_uptime(NOW, self.log(beats))
        self.assertEqual(r.state, WARN)
        self.assertLess(r.value, 0.98)
        self.assertIn("uyku/askı 20 saat", r.text)

    def test_a_restart_is_counted(self):
        start = NOW - timedelta(days=7)
        beats = [(start + timedelta(minutes=5 * i), 1 if i < 500 else 2) for i in range(7 * 24 * 12 + 1)]
        self.assertIn("1 yeniden başlama", slo.bot_uptime(NOW, self.log(beats)).text)

    def test_less_than_a_day_of_records_is_unknown(self):
        beats = [(NOW - timedelta(minutes=5 * i), 1) for i in range(20)]
        r = slo.bot_uptime(NOW, self.log(beats))
        self.assertEqual(r.state, UNKNOWN)
        self.assertIn("birikiyor", r.text)

    def test_heartbeat_record_is_appended(self):
        path = self.dir / "hb.csv"
        slo.record_heartbeat(path, NOW, pid=42)
        slo.record_heartbeat(path, NOW + timedelta(minutes=5), pid=42)
        self.assertEqual(path.read_text(encoding="utf-8").splitlines()[1:],
                         ["2026-11-06T21:00:00+03:00,42", "2026-11-06T21:05:00+03:00,42"])


class FreshnessTest(Temp):
    def test_days_with_enough_closes(self):
        path = self.dir / "freshness.csv"
        for d in WEEK:
            slo.record_freshness(d, have=99 if d != WEEK[2] else 90, total=100, xu100=True,
                                 path=path, now=datetime.combine(d, datetime.min.time(), ISTANBUL).replace(hour=18, minute=35))
        r = slo.freshness(NOW, path)
        self.assertEqual(r.state, WARN)
        self.assertAlmostEqual(r.value, 4 / 5)
        self.assertIn("04.11 %90", r.text)

    def test_missing_index_close_fails_the_day(self):
        path = self.dir / "freshness.csv"
        for d in WEEK:
            slo.record_freshness(d, 100, 100, xu100=d != WEEK[0], path=path,
                                 now=datetime.combine(d, datetime.min.time(), ISTANBUL).replace(hour=18, minute=35))
        self.assertIn("02.11 XU100 yok", slo.freshness(NOW, path).text)

    def test_no_record_is_unknown(self):
        self.assertEqual(slo.freshness(NOW, self.dir / "yok.csv").state, UNKNOWN)


class BackupSloTest(Temp):
    def test_daily_backups_and_restore_test(self):
        folder = self.dir / "yedek"
        folder.mkdir()
        for d in WEEK:
            (folder / f"quantbist_{d.isoformat()}.zip").write_bytes(b"x")
        restores = self.dir / "restore_tests.csv"
        slo.record_restore_test(True, "3 dosya", path=restores, now=NOW - timedelta(days=2))
        r = slo.backup_slo(NOW, folder, restores)
        self.assertEqual(r.state, OK, r.text)
        self.assertIn("5/5", r.text)

    def test_failed_or_missing_restore_test(self):
        folder = self.dir / "yedek"
        folder.mkdir()
        for d in WEEK:
            (folder / f"quantbist_{d.isoformat()}.zip").write_bytes(b"x")
        restores = self.dir / "restore_tests.csv"
        # never recorded (the record started with v0.51.0): not measured, so unknown, never a failure
        never = slo.backup_slo(NOW, folder, restores)
        self.assertEqual(never.state, UNKNOWN)
        self.assertIn("henüz kaydedilmedi", never.text)
        slo.record_restore_test(True, "eski", path=restores, now=NOW - timedelta(days=10))
        self.assertEqual(slo.backup_slo(NOW, folder, restores).state, WARN)  # recorded, but none in 7 days
        slo.record_restore_test(False, "zip bozuk", path=restores, now=NOW - timedelta(days=1))
        r = slo.backup_slo(NOW, folder, restores)
        self.assertEqual(r.state, WARN)
        self.assertIn("başarısız", r.text)


class AccuracySloTest(Temp):
    def summary(self, days_ago=1, differing=(), checked=100):
        d = (NOW - timedelta(days=days_ago)).date().isoformat()
        return {"date": d, "checked": checked, "differing": list(differing), "unchecked": [],
                "share": len(differing) / checked}

    def test_within_one_percent(self):
        r = slo.accuracy(NOW, self.summary(differing=["AAA"]))
        self.assertEqual(r.state, OK)
        self.assertIn("1/100", r.text)

    def test_above_one_percent_names_the_stocks(self):
        r = slo.accuracy(NOW, self.summary(differing=["AAA", "BBB"]))
        self.assertEqual(r.state, WARN)
        self.assertIn("şüpheli: AAA, BBB", r.text)

    def test_old_or_missing_result_is_unknown(self):
        self.assertEqual(slo.accuracy(NOW, None).state, UNKNOWN)
        self.assertEqual(slo.accuracy(NOW, self.summary(days_ago=9)).state, UNKNOWN)


class QualitySloTest(Temp):
    def get(self, conclusion, minutes_ago=30):
        from types import SimpleNamespace

        started = (NOW - timedelta(minutes=minutes_ago)).astimezone(__import__("datetime").timezone.utc)
        body = {"workflow_runs": [{"status": "completed", "conclusion": conclusion, "head_sha": "abc1234def",
                                   "run_started_at": started.strftime("%Y-%m-%dT%H:%M:%SZ")}]}
        return lambda *a, **k: SimpleNamespace(raise_for_status=lambda: None, json=lambda: body)

    def test_green_ci_with_the_coverage_gate(self):
        r = slo.quality(NOW, get=self.get("success"))
        self.assertEqual(r.state, OK)
        self.assertIn(f"kapsam kapısı %{slo.COVERAGE_GATE}", r.text)

    def test_red_ci(self):
        r = slo.quality(NOW, get=self.get("failure"))
        self.assertEqual(r.state, WARN)
        self.assertIn("abc1234", r.text)

    def test_offline_is_unknown(self):
        def offline(*a, **k):
            raise OSError("ağ yok")

        self.assertEqual(slo.quality(NOW, get=offline).state, UNKNOWN)

    def test_gate_matches_the_ci_workflow(self):
        ci = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn(f"--cov-fail-under={slo.COVERAGE_GATE}", ci)
        self.assertGreaterEqual(slo.COVERAGE_GATE, 90)  # CHARTER §2


class AllSloTest(Temp):
    def test_unmeasured_objectives_are_unknown_never_ok(self):
        results = slo.measure(NOW, folder=self.dir)
        names = [r.name for r in results]
        self.assertEqual(names, list(slo.TARGETS))
        by = {r.name: r for r in results}
        self.assertEqual(by["Veri doğruluğu"].state, UNKNOWN)  # tests are offline: no summary to read
        self.assertEqual(by["Kalite (CI, kapsam)"].state, UNKNOWN)
        self.assertTrue(all(r.state != OK for r in results))  # empty folder: nothing is measurable

    def test_lines_for_durum(self):
        lines = slo.lines(slo.measure(NOW, folder=self.dir))
        self.assertTrue(lines[0].startswith("📐 SLO (son 7 gün)"))
        self.assertTrue(any("Rapor teslimi" in line and "hedef ≥ %99" in line for line in lines))



class WiringTest(Temp):
    """The records behind the objectives are written by the bot and the daily report (conftest keeps them private)."""

    def test_live_heartbeat_also_extends_the_history(self):
        from unittest import mock

        from core.reports import health

        with mock.patch.object(health, "HEARTBEAT_FILE", self.dir / "heartbeat.txt"):
            health.write_heartbeat(now=NOW)  # no path: the live call the bot makes
        self.assertIn("2026-11-06T21:00:00+03:00", slo.HEARTBEATS_FILE.read_text(encoding="utf-8"))

    def test_daily_update_records_freshness(self):
        from unittest import mock

        from core.market import store
        from core.market.universe import BENCHMARK
        from core.reports import daily
        from tests.helpers import offline_market

        with offline_market():
            store.update([BENCHMARK, "AAA.IS", "BBB.IS"])
            last = store.last_date(BENCHMARK)
            with mock.patch.object(daily, "last_final_session_date", return_value=last):
                daily._record_freshness(["AAA.IS", "BBB.IS"], now=NOW)
        row = slo.FRESHNESS_FILE.read_text(encoding="utf-8").splitlines()[1].split(",")
        self.assertEqual((row[0], row[2], row[3], row[4]), (last.isoformat(), "2", "2", "1"))

    def test_durum_shows_the_objectives(self):
        from core.reports import health

        text = health.health_report(NOW, bars=lambda s: __import__("pandas").DataFrame())
        self.assertIn("📐 SLO (son 7 gün)", text)
        self.assertIn("Veri doğruluğu", text)


if __name__ == "__main__":
    unittest.main()
