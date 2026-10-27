"""The installation proof must be complete, keep going past a failed section and never leak secrets."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from core.reports import verify

TOKEN = "1234567890:AAH" + "x" * 32
SECRETS = {"BOT_TOKEN": TOKEN, "CHAT_ID": "1790584407"}


class RedactTest(unittest.TestCase):
    def test_token_and_chat_id_are_replaced(self):
        text = verify.redact(f"token={TOKEN} chat 1790584407 son", SECRETS)
        self.assertNotIn(TOKEN, text)
        self.assertNotIn("1790584407", text)
        self.assertIn("[BOT_TOKEN]", text)
        self.assertIn("[CHAT_ID]", text)

    def test_any_token_shaped_text_is_replaced(self):
        other = "987654321:" + "B" * 35
        self.assertEqual(verify.redact(f"x {other} y", {}), "x [BOT_TOKEN] y")

    def test_ordinary_numbers_stay(self):
        self.assertEqual(verify.redact("2026-10-27 18:30 sent 117", {"CHAT_ID": ""}), "2026-10-27 18:30 sent 117")


class ReportTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def test_sections_and_a_failing_section_does_not_stop_the_rest(self):
        log = self.root / "daily_2026-10-27.log"
        log.write_text("\n".join(f"satır {i}" for i in range(50)) + f"\nsend ok {TOKEN}\n", encoding="utf-8")
        runs = self.root / "runs.csv"
        runs.write_text("header\n" + "\n".join(f"row{i}" for i in range(10)) + "\n", encoding="utf-8")

        def broken():
            raise OSError("disk yok")

        with mock.patch.object(verify, "_health", return_value="✅ SAĞLIKLI"), \
                mock.patch.object(verify, "_backup", side_effect=broken):
            text = verify.verify_report(secrets=SECRETS, runs_file=runs, log_dir=self.root)

        self.assertIn("doğrulama raporu", text)
        self.assertIn("✅ SAĞLIKLI", text)
        self.assertIn("HATA: OSError: disk yok", text)
        self.assertIn("header", text)
        self.assertIn("row9", text)
        self.assertNotIn("row2", text)  # only the last rows
        self.assertIn("daily_2026-10-27.log", text)
        self.assertNotIn("satır 0\n", text)
        self.assertNotIn(TOKEN, text)

    def test_missing_files_are_reported(self):
        self.assertIn("yok", verify._runs(self.root / "runs.csv"))
        self.assertIn("yok", verify._daily_log(self.root))


if __name__ == "__main__":
    unittest.main()


class BackupSectionTest(unittest.TestCase):
    def test_snapshot_and_restore_test_in_isolated_folders(self):
        import sqlite3

        from core import backup

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / "market.db"
            conn = sqlite3.connect(db)
            conn.execute("CREATE TABLE t (x)")
            conn.execute("INSERT INTO t VALUES (1)")
            conn.commit()
            conn.close()
            before = db.read_bytes()
            with mock.patch.object(backup, "MARKET_DB", db), \
                    mock.patch.dict("os.environ", {"BACKUP_DIR": str(root / "yedek")}):
                text = verify._backup()
            self.assertIn("Geri yükleme testi başarılı", text)
            self.assertIn("bütünlük ok", text)
            self.assertTrue(list((root / "yedek").glob("quantbist_marketdb_*.zip")))
            self.assertEqual(db.read_bytes(), before)  # the live store is not touched


class WindowsConsoleTest(unittest.TestCase):
    """On the user's PC stdout is cp1254: printing the report's emoji crashed verify (27.10.2026)."""

    def test_main_prints_emoji_on_a_cp1254_console(self):
        import io

        raw = io.BytesIO()
        console = io.TextIOWrapper(raw, encoding="cp1254")
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(verify, "verify_report", return_value="🩺 durum ✅"), \
                mock.patch("sys.stdout", console):
            code = verify.main(["--no-backup", "--out", str(Path(tmp) / "r.txt")])
            console.flush()
        self.assertEqual(code, 0)
        self.assertIn("🩺 durum ✅", raw.getvalue().decode("utf-8"))

    def test_other_commands_run_on_the_pc_print_emoji_too(self):
        import io

        from core import backup
        from core.reports import forward, health

        cases = [
            (health, "health_report", "🩺 SAĞLIKLI", lambda: health.main([])),
            (forward, "forward_report", "📏 ölçüm", lambda: forward.main([])),
            (backup, "backup_market_db", None, lambda: backup.main(["--market-db"])),
        ]
        for module, name, text, run in cases:
            with self.subTest(module.__name__):
                raw = io.BytesIO()
                console = io.TextIOWrapper(raw, encoding="cp1254")
                value = text if text is not None else backup.Backup(Path("quantbist_marketdb_x.zip"), ["market.db"])
                with mock.patch.object(module, name, return_value=value), mock.patch("sys.stdout", console):
                    run()
                    console.flush()
                self.assertTrue(any(ch in raw.getvalue().decode("utf-8") for ch in "🩺📏💾"))
