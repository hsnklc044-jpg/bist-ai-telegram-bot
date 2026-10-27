"""Backups must be restorable, not just present: isolated restore tests and the SQLite snapshot."""

import sqlite3
import tempfile
import unittest
import zipfile
from datetime import date
from pathlib import Path
from unittest import mock

from core import backup
from core.reports import daily

LEDGER = "id,date,account,symbol,side,quantity,price,fee,note\n1,2026-10-01,real,THYAO.IS,buy,10,100,1,\n"
ORDERS = "id,created_at,symbol,side,quantity,status,fill_date,fill_price,note\n1,2026-10-20T10:00:00+03:00,THYAO.IS,buy,10,pending,,,\n"


class RestoreTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.data, self.target = self.root / "data", self.root / "backups"
        self.data.mkdir()
        (self.data / "ledger.csv").write_text(LEDGER, encoding="utf-8")
        (self.data / "paper_orders.csv").write_text(ORDERS, encoding="utf-8")
        (self.data / "watchlist.json").write_text('{"42": ["EREGL.IS"]}', encoding="utf-8")
        self.db = self.data / "market.db"
        conn = sqlite3.connect(self.db)
        conn.execute("CREATE TABLE candles (symbol TEXT, day TEXT, close REAL)")
        conn.execute("INSERT INTO candles VALUES ('THYAO.IS', '2026-10-23', 258.0)")
        conn.commit()
        conn.close()
        self.files = [self.data / n for n in ("ledger.csv", "paper_orders.csv", "watchlist.json")]

    def test_restore_reads_every_file_and_leaves_live_files_alone(self):
        b = backup.create_backup(self.files, target=self.target)
        snap = backup.backup_market_db(self.db, target=self.target)
        before = {p.name: p.read_bytes() for p in self.data.iterdir()}

        lines = backup.test_restore([b.path, snap.path])

        text = "\n".join(lines)
        self.assertIn("defter 1 satır", text)
        self.assertIn("sanal emir 1", text)
        self.assertIn("takip listesi 1 kullanıcı", text)
        self.assertIn("fiyat veritabanı bütünlük ok", text)
        self.assertEqual({p.name: p.read_bytes() for p in self.data.iterdir()}, before)

    def test_corrupt_backup_is_detected(self):
        b = backup.create_backup(self.files, target=self.target)
        with zipfile.ZipFile(b.path) as zf:
            content = {n: zf.read(n) for n in zf.namelist()}
        content["ledger.csv"] = b"bozuk"  # manifest unchanged: the hash no longer matches
        with zipfile.ZipFile(b.path, "w") as zf:
            for name, data in content.items():
                zf.writestr(name, data)
        with self.assertRaisesRegex(backup.BackupError, "bozuk"):
            backup.test_restore([b.path])

    def test_unreadable_content_fails_the_test(self):
        (self.data / "ledger.csv").write_text(LEDGER + "2,xx,real,THYAO.IS,buy,abc,1,0,\n", encoding="utf-8")
        b = backup.create_backup(self.files, target=self.target)  # hashes match, content is bad
        with self.assertRaisesRegex(backup.BackupError, "okunamadı"):
            backup.test_restore([b.path])

    def test_missing_backup_is_an_error(self):
        with mock.patch.object(backup, "backup_dir", return_value=self.target):
            with self.assertRaisesRegex(backup.BackupError, "yedek yok"):
                backup.test_restore()

    def test_snapshot_while_another_connection_writes(self):
        writer = sqlite3.connect(self.db)
        writer.execute("BEGIN")
        writer.execute("INSERT INTO candles VALUES ('EREGL.IS', '2026-10-23', 40.0)")  # not committed
        snap = backup.backup_market_db(self.db, target=self.target)
        writer.rollback()
        writer.close()
        self.assertIn("bütünlük ok", "\n".join(backup.test_restore([snap.path])))

    def test_snapshot_rotation_and_daily_list_are_separate(self):
        for d in ("2026-10-01", "2026-10-08", "2026-10-15", "2026-10-22", "2026-10-29"):
            with mock.patch.object(backup, "date") as fake:
                fake.today.return_value = date.fromisoformat(d)
                backup.backup_market_db(self.db, target=self.target)
        backup.create_backup(self.files, target=self.target)
        self.assertEqual(len(backup.market_db_backups(self.target)), backup.MARKET_DB_KEEP)
        self.assertTrue(all("marketdb" not in p.name for p in backup.daily_backups(self.target)))


class WeeklyCheckInReportTest(unittest.TestCase):
    def test_runs_weekly_and_reports_failure_without_stopping(self):
        with mock.patch.object(backup, "market_db_backups", return_value=[Path("quantbist_marketdb_2026-10-24.zip")]):
            self.assertEqual(daily._weekly_backup_check(date(2026, 10, 26)), "")  # 2 days old: skip

        with mock.patch.object(backup, "market_db_backups", return_value=[]), \
                mock.patch.object(backup, "backup_market_db"), \
                mock.patch.object(backup, "test_restore", return_value=["a", "b"]):
            self.assertIn("başarılı: 2 dosya", daily._weekly_backup_check(date(2026, 10, 26)))

        with mock.patch.object(backup, "market_db_backups", return_value=[]), \
                mock.patch.object(backup, "backup_market_db", side_effect=OSError("disk dolu")):
            self.assertIn("başarısız: disk dolu", daily._weekly_backup_check(date(2026, 10, 26)))


class CommandLineRestoreTestIsRecordedTest(unittest.TestCase):
    """DR drill 27.10 (run 40551266369): `--test-restore` passed, but the Yedek SLO still said
    "geri yükleme testi sonucu henüz kaydedilmedi"; manual and monthly tests were never counted."""

    def test_success_and_failure_are_recorded_for_the_slo(self):
        from core.reports import slo

        with mock.patch.object(backup, "test_restore", return_value=["a", "b"]):
            self.assertEqual(backup.main(["--test-restore"]), 0)
        with mock.patch.object(backup, "test_restore", side_effect=backup.BackupError("bozuk zip")):
            self.assertEqual(backup.main(["--test-restore"]), 1)

        rows = slo.RESTORE_FILE.read_text(encoding="utf-8").splitlines()
        self.assertEqual(rows[0], "at,ok,detail")
        self.assertEqual([r.split(",")[1] for r in rows[1:]], ["1", "0"])
        self.assertIn("bozuk zip", rows[2])

    def test_pulled_server_copies_are_not_this_machines_backup_slo(self):
        """pull_backups checks copies of the server's backups; they say nothing about this PC's chain
        (and the test running the script in a subprocess wrote to the real logs/ - write guard)."""
        from core.reports import slo

        with mock.patch.object(backup, "test_restore", return_value=["a"]):
            self.assertEqual(backup.main(["--test-restore", "--no-record"]), 0)
        self.assertFalse(slo.RESTORE_FILE.exists())
        root = Path(__file__).resolve().parents[1] / "scripts"
        for script in ("pull_backups.sh", "pull_backups.ps1"):
            self.assertIn("--test-restore --no-record", (root / script).read_text(encoding="utf-8"), script)


if __name__ == "__main__":
    unittest.main()
