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

    def make_signals_db(self, signals=1, breaker=1):
        from core.signals import store

        path = self.data / "signals.db"
        conn = store.connect(path)
        for i in range(signals):
            conn.execute("INSERT INTO signals (created, symbol, signal_close, source) VALUES (?, ?, 10.0, 'test')",
                         (f"2026-11-0{i + 1}", f"S{i}.IS"))
        for i in range(breaker):
            conn.execute("INSERT INTO breaker (day, change) VALUES (?, -0.07)", (f"2026-11-0{i + 1}",))
        conn.commit()
        conn.close()
        return path

    def restore_signals(self):
        b = backup.create_backup([*self.files, self.data / "signals.db"], target=self.target)  # hashes match
        return backup.test_restore([b.path])

    def test_signals_db_is_read_as_sqlite_not_as_csv(self):
        self.make_signals_db(signals=2, breaker=1)
        before = (self.data / "signals.db").read_bytes()
        text = "\n".join(self.restore_signals())
        self.assertIn("sinyal defteri bütünlük ok (2 sinyal, 1 devre kesici günü)", text)
        self.assertEqual((self.data / "signals.db").read_bytes(), before)

    def test_an_empty_signal_book_is_a_valid_restore(self):
        self.make_signals_db(signals=0, breaker=0)
        self.assertIn("(0 sinyal, 0 devre kesici günü)", "\n".join(self.restore_signals()))

    def test_committed_rows_still_in_the_wal_file_are_in_the_backup(self):
        path = self.make_signals_db(signals=1, breaker=0)
        writer = sqlite3.connect(path)  # stays open: the WAL is not folded into the main file
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("INSERT INTO signals (created, symbol, signal_close, source) VALUES ('2026-11-09', 'WAL.IS', 5.0, 't')")
        writer.commit()
        self.addCleanup(writer.close)
        self.assertNotEqual(len(path.read_bytes()), 0)
        self.assertIn("(2 sinyal, 0 devre kesici günü)", "\n".join(self.restore_signals()))

    def test_an_uncommitted_write_is_not_in_the_backup(self):
        path = self.make_signals_db(signals=1, breaker=0)
        writer = sqlite3.connect(path)
        writer.execute("BEGIN")
        writer.execute("INSERT INTO signals (created, symbol, signal_close, source) VALUES ('2026-11-09', 'X.IS', 5.0, 't')")
        self.addCleanup(writer.close)
        self.assertIn("(1 sinyal, 0 devre kesici günü)", "\n".join(self.restore_signals()))

    def test_a_failed_snapshot_falls_back_to_the_plain_copy_and_logs(self):
        path = self.make_signals_db(signals=1)
        real = sqlite3.connect
        with mock.patch("sqlite3.connect", side_effect=sqlite3.DatabaseError("kilitli")), \
                self.assertLogs("core.backup", level="WARNING") as logs:
            data = backup._backup_bytes(path)
        self.assertEqual(data, path.read_bytes())
        self.assertIn("backed up as it is", logs.output[0])
        self.assertIs(sqlite3.connect, real)

    def test_a_plain_file_and_a_non_sqlite_db_are_copied_as_they_are(self):
        csv_file = self.data / "ledger.csv"
        self.assertEqual(backup._backup_bytes(csv_file), csv_file.read_bytes())
        fake = self.data / "other.db"
        fake.write_bytes(b"not sqlite")
        self.assertEqual(backup._backup_bytes(fake), b"not sqlite")

    def test_a_file_that_is_not_a_database_is_rejected_with_a_clear_error(self):
        (self.data / "signals.db").write_text("id,created\n1,2026-11-01\n", encoding="utf-8")  # a CSV by name
        with self.assertRaisesRegex(backup.BackupError, r"signals\.db geri yüklendi ama okunamadı"):
            self.restore_signals()

    def test_a_damaged_database_is_rejected(self):
        path = self.make_signals_db(signals=1)
        data = path.read_bytes()
        path.write_bytes(data[: len(data) // 2] + b"\xb9" * (len(data) - len(data) // 2))
        with self.assertRaisesRegex(backup.BackupError, r"signals\.db"):
            self.restore_signals()

    def test_a_database_without_the_expected_tables_is_rejected(self):
        path = self.data / "signals.db"
        conn = sqlite3.connect(path)
        conn.execute("CREATE TABLE other (x INTEGER)")
        conn.commit()
        conn.close()
        with self.assertRaisesRegex(backup.BackupError, "beklenen tablo yok: signals, breaker"):
            self.restore_signals()

    def test_a_database_with_a_missing_column_fails_on_the_apps_own_query(self):
        path = self.data / "signals.db"
        conn = sqlite3.connect(path)
        conn.execute("CREATE TABLE signals (id INTEGER PRIMARY KEY, created TEXT)")
        conn.execute("CREATE TABLE breaker (day TEXT, change REAL)")
        conn.commit()
        conn.close()
        with self.assertRaisesRegex(backup.BackupError, "okunamadı"):
            self.restore_signals()

    def test_the_encoding_error_is_not_hidden_for_a_text_file(self):
        (self.data / "ledger.csv").write_bytes(b"id,date\n1,\xb9\xb9\n")
        b = backup.create_backup(self.files, target=self.target)
        with self.assertRaisesRegex(backup.BackupError, "okunamadı"):
            backup.test_restore([b.path])

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
