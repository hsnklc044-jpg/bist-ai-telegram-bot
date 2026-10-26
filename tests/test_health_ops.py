"""Operational health checks: database, disk, bot heartbeat, data schema, GitHub research."""

import sqlite3
import tempfile
import unittest
from collections import namedtuple
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from core.market.calendar import ISTANBUL
from core.reports import daily, health

NOW = datetime(2026, 10, 26, 20, 0, tzinfo=ISTANBUL)


class Temp(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)


class DatabaseTest(Temp):
    def test_ok_missing_and_corrupt(self):
        db = self.root / "market.db"
        self.assertEqual(health.database_check(db).state, health.UNKNOWN)

        conn = sqlite3.connect(db)
        conn.execute("CREATE TABLE t (x)")
        conn.commit()
        conn.close()
        self.assertEqual(health.database_check(db).state, health.OK)

        db.write_bytes(b"SQLite format 3\x00" + b"\x00" * 100 + b"bozuk" * 200)
        self.assertEqual(health.database_check(db).state, health.CRIT)

    def test_locked_by_a_writer_is_a_warning_not_damage(self):
        db = self.root / "market.db"
        conn = sqlite3.connect(db)
        conn.execute("CREATE TABLE t (x)")
        conn.commit()
        conn.execute("BEGIN EXCLUSIVE")  # a writer holds the store
        self.addCleanup(conn.close)
        with mock.patch.object(health, "DB_TIMEOUT", 0.1):
            check = health.database_check(db)
        self.assertEqual(check.state, health.WARN)
        self.assertIn("kilitli", check.text)
        conn.rollback()
        self.assertEqual(health.database_check(db).state, health.OK)


class DiskTest(Temp):
    def test_thresholds(self):
        usage = namedtuple("usage", "total used free")
        for free, state in ((5e9, health.OK), (5e8, health.WARN), (1e8, health.CRIT)):
            with self.subTest(free=free), mock.patch("shutil.disk_usage", return_value=usage(0, 0, int(free))):
                self.assertEqual(health.disk_check(self.root).state, state)


class HeartbeatTest(Temp):
    def test_fresh_stale_missing(self):
        beat = self.root / "heartbeat.txt"
        self.assertEqual(health.bot_check(NOW, beat).state, health.UNKNOWN)

        health.write_heartbeat(beat, NOW - timedelta(minutes=4))
        self.assertEqual(health.bot_check(NOW, beat).state, health.OK)

        health.write_heartbeat(beat, NOW - timedelta(hours=3))
        check = health.bot_check(NOW, beat)
        self.assertEqual(check.state, health.CRIT)
        self.assertIn("3.0 saattir", check.text)


class SchemaTest(Temp):
    def test_required_columns(self):
        ledger = self.root / "ledger.csv"
        orders = self.root / "paper_orders.csv"
        schemas = {ledger: health.SCHEMAS[health.LEDGER_FILE], orders: health.SCHEMAS[health.PAPER_ORDERS_FILE]}
        self.assertEqual(health.schema_check(schemas).state, health.UNKNOWN)

        ledger.write_text("id,date,account,symbol,side,quantity,price,fee,note\n", encoding="utf-8")
        # a pre-v0.28 orders file (no extra columns) is still readable: OK
        orders.write_text("id,created_at,symbol,side,quantity,status,fill_date,fill_price,note\n", encoding="utf-8")
        self.assertEqual(health.schema_check(schemas).state, health.OK)

        ledger.write_text("id,date,account,symbol\n", encoding="utf-8")
        check = health.schema_check(schemas)
        self.assertEqual(check.state, health.CRIT)
        self.assertIn("ledger.csv eksik sütun", check.text)


class ResearchTest(unittest.TestCase):
    def _get(self, runs=None, fail=False):
        def get(url, params=None, timeout=None):
            if fail:
                raise OSError("ağ yok")
            return SimpleNamespace(raise_for_status=lambda: None, json=lambda: {"workflow_runs": runs})
        return get

    def run_(self, conclusion, days_ago):
        started = (NOW - timedelta(days=days_ago)).astimezone(ISTANBUL).isoformat()
        return {"status": "completed", "conclusion": conclusion, "run_started_at": started}

    def test_states(self):
        self.assertEqual(health.research_check(NOW, self._get([self.run_("success", 2)])).state, health.OK)
        self.assertEqual(health.research_check(NOW, self._get([self.run_("failure", 2)])).state, health.WARN)
        self.assertEqual(health.research_check(NOW, self._get([self.run_("success", 12)])).state, health.WARN)
        self.assertEqual(health.research_check(NOW, self._get(fail=True)).state, health.UNKNOWN)
        self.assertEqual(health.research_check(NOW, self._get([])).state, health.UNKNOWN)

    def test_tests_never_reach_the_network(self):
        self.assertEqual(health.research_check(NOW).state, health.UNKNOWN)


class ReportWarningsTest(Temp):
    def test_bot_down_shows_in_the_daily_report(self):
        down = health.Check("Telegram botu", health.CRIT, "3.0 saattir yaşam sinyali yok")
        ok = health.Check("X", health.OK, "")
        with mock.patch.object(health, "bot_check", return_value=down), \
                mock.patch.object(health, "database_check", return_value=ok), \
                mock.patch.object(health, "disk_check", return_value=ok), \
                mock.patch.object(health, "schema_check", return_value=ok):
            text = daily._with_health_warnings(f"rapor\n\n{daily.DISCLAIMER}")
        self.assertIn("KRİTİK · Telegram botu", text)
        self.assertLess(text.index("Telegram botu"), text.index(daily.DISCLAIMER))

    def test_nothing_added_when_healthy_or_unknown(self):
        ok = health.Check("X", health.OK, "")
        unknown = health.Check("Telegram botu", health.UNKNOWN, "")
        with mock.patch.object(health, "bot_check", return_value=unknown), \
                mock.patch.object(health, "database_check", return_value=ok), \
                mock.patch.object(health, "disk_check", return_value=ok), \
                mock.patch.object(health, "schema_check", return_value=ok):
            self.assertEqual(daily._with_health_warnings("rapor"), "rapor")

    def test_failure_never_stops_the_report(self):
        with mock.patch.object(health, "bot_check", side_effect=RuntimeError("x")):
            self.assertIn("Sağlık kontrolü yapılamadı", daily._with_health_warnings("rapor"))


if __name__ == "__main__":
    unittest.main()


class BackupLocationTest(Temp):
    """A backup on the same disk as the data is lost with it (Aşama 2: separate physical target)."""

    def _fresh_backup(self, folder):
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / "quantbist_2026-10-26.zip"
        path.write_bytes(b"x")
        stamp = NOW.timestamp() - 3600
        import os

        os.utime(path, (stamp, stamp))

    def test_inside_the_project_is_a_warning(self):
        data = self.root / "data"
        self._fresh_backup(data / "backups")
        check = health.backup_check(NOW, data / "backups", data_dir=data)
        self.assertEqual(check.state, health.WARN)
        self.assertIn("BACKUP_DIR", check.text)

    def test_same_disk_is_a_warning(self):
        data = self.root / "data"
        data.mkdir()
        self._fresh_backup(self.root / "yedek")
        check = health.backup_check(NOW, self.root / "yedek", data_dir=data)
        self.assertEqual(check.state, health.WARN)
        self.assertIn("aynı disk", check.text)

    def test_synced_folder_or_other_disk_is_ok(self):
        data = self.root / "data"
        data.mkdir()
        self._fresh_backup(self.root / "OneDrive" / "QuantBIST")
        self.assertEqual(health.backup_check(NOW, self.root / "OneDrive" / "QuantBIST", data_dir=data).state, health.OK)

        self._fresh_backup(self.root / "usb")
        real = health._device
        with mock.patch.object(health, "_device", side_effect=lambda p: real(p) + (1 if p.name == "usb" else 0)):
            self.assertEqual(health.backup_check(NOW, self.root / "usb", data_dir=data).state, health.OK)


class ContainerHealthTest(Temp):
    """docker compose asks `python -m core.reports.health --heartbeat`: 0 alive, 1 not."""

    def test_exit_code_follows_the_heartbeat(self):
        path = self.root / "heartbeat.txt"
        with mock.patch.object(health, "HEARTBEAT_FILE", path), \
                mock.patch.object(health, "now_istanbul", return_value=NOW):
            self.assertEqual(health.main(["--heartbeat"]), 1)  # no heartbeat yet
            health.write_heartbeat(path, now=NOW - timedelta(minutes=3))
            self.assertEqual(health.main(["--heartbeat"]), 0)
            health.write_heartbeat(path, now=NOW - timedelta(hours=2))
            self.assertEqual(health.main(["--heartbeat"]), 1)

    def test_without_arguments_prints_the_report(self):
        with mock.patch.object(health, "health_report", return_value="🩺 rapor") as report, \
                mock.patch("builtins.print") as out:
            self.assertEqual(health.main([]), 0)
        report.assert_called_once()
        out.assert_called_once_with("🩺 rapor")


class PulledBackupTest(Temp):
    """On a server the backups sit on the data disk; scripts/pull_backups copies them off and leaves pulled.txt."""

    def setUp(self):
        super().setUp()
        self.data = self.root / "data"
        self.data.mkdir()
        self.target = self.root / "yedek"
        BackupLocationTest._fresh_backup(self, self.target)

    def check(self):
        return health.backup_check(NOW, self.target, data_dir=self.data)

    def test_recent_pull_counts_as_a_separate_copy(self):
        (self.target / health.PULL_MARKER).write_text((NOW - timedelta(days=1)).isoformat(), encoding="utf-8")
        check = self.check()
        self.assertEqual(check.state, health.OK)
        self.assertIn("PC'ye alındı", check.text)

    def test_old_pull_is_a_warning(self):
        (self.target / health.PULL_MARKER).write_text((NOW - timedelta(days=9)).isoformat(), encoding="utf-8")
        check = self.check()
        self.assertEqual(check.state, health.WARN)
        self.assertIn("9 gündür", check.text)

    def test_marker_without_time_zone_is_istanbul_time(self):
        (self.target / health.PULL_MARKER).write_text("2026-10-26T08:00:00", encoding="utf-8")
        self.assertEqual(self.check().state, health.OK)

    def test_unreadable_marker_is_not_trusted(self):
        (self.target / health.PULL_MARKER).write_text("dün", encoding="utf-8")
        self.assertEqual(self.check().state, health.WARN)
