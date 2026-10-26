import json
import tempfile
import unittest
import zipfile
from datetime import date
from pathlib import Path
from unittest import mock

from core import backup
from core.reports import daily


class BackupTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.data = self.root / "data"
        self.data.mkdir()
        self.target = self.root / "backups"
        self.files = [self.data / "ledger.csv", self.data / "watchlist.json", self.data / "missing.csv"]
        self.files[0].write_text("id,date\n1,2026-10-26\n", encoding="utf-8")
        self.files[1].write_text('{"1": ["THYAO.IS"]}', encoding="utf-8")

    def test_backup_contains_existing_files_and_verifies(self):
        result = backup.create_backup(self.files, target=self.target)

        self.assertEqual(result.files, ["ledger.csv", "watchlist.json"])
        self.assertEqual(sorted(backup.verify(result.path)), ["ledger.csv", "watchlist.json"])
        self.assertIn("doğrulandı", result.line())
        self.assertFalse(list(self.target.glob("*.tmp")))

    def test_nothing_to_back_up(self):
        self.assertIsNone(backup.create_backup([self.data / "none.csv"], target=self.target))

    def test_corruption_is_detected(self):
        path = backup.create_backup(self.files, target=self.target).path
        with zipfile.ZipFile(path) as zf:
            manifest = zf.read(backup.MANIFEST)
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("ledger.csv", "tampered")
            zf.writestr("watchlist.json", "{}")
            zf.writestr(backup.MANIFEST, manifest)

        with self.assertRaises(backup.BackupError):
            backup.verify(path)

    def test_rotation_keeps_newest_daily_backups(self):
        for day in range(1, 6):
            backup.create_backup(self.files, target=self.target, name=f"quantbist_2026-10-0{day}.zip")
        backup.create_backup(self.files, target=self.target, name="quantbist_before_restore_x.zip")

        with mock.patch.object(backup, "date") as fake:
            fake.today.return_value = date(2026, 10, 26)
            backup.create_backup(self.files, target=self.target, keep=3)

        names = sorted(p.name for p in self.target.glob("*.zip"))
        self.assertEqual(
            names,
            [
                "quantbist_2026-10-04.zip",
                "quantbist_2026-10-05.zip",
                "quantbist_2026-10-26.zip",
                "quantbist_before_restore_x.zip",
            ],
        )

    def test_restore_round_trip_with_safety_copy(self):
        saved = backup.create_backup(self.files, target=self.target).path
        self.files[0].write_text("id,date\n1,2026-10-26\n2,BROKEN\n", encoding="utf-8")

        names, safety = backup.restore_backup(saved, data_dir=self.data)

        self.assertEqual(names, ["ledger.csv", "watchlist.json"])
        self.assertEqual(self.files[0].read_text(encoding="utf-8"), "id,date\n1,2026-10-26\n")
        with zipfile.ZipFile(safety.path) as zf:
            self.assertIn("BROKEN", zf.read("ledger.csv").decode())
            self.assertEqual(sorted(json.loads(zf.read(backup.MANIFEST))["files"]),
                             ["ledger.csv", "watchlist.json"])

    def test_backup_dir_from_env(self):
        with mock.patch.dict("os.environ", {"BACKUP_DIR": str(self.target)}):
            self.assertEqual(backup.backup_dir(), self.target)


class DailyIntegrationTest(unittest.TestCase):
    def test_report_gets_backup_line_before_disclaimer(self):
        text = f"rapor\n\n{daily.DISCLAIMER}"
        fake = backup.Backup(path=Path("quantbist_2026-10-26.zip"), files=["ledger.csv"])

        with mock.patch("core.backup.create_backup", return_value=fake):
            out = daily._with_backup_line(text)

        self.assertTrue(out.endswith(daily.DISCLAIMER))
        self.assertIn("💾 Yedek: quantbist_2026-10-26.zip (1 dosya, doğrulandı)", out)

    def test_failed_backup_never_stops_the_report(self):
        with mock.patch("core.backup.create_backup", side_effect=OSError("disk dolu")):
            out = daily._with_backup_line(f"rapor\n\n{daily.DISCLAIMER}")

        self.assertIn("⚠️ Yedek alınamadı: disk dolu", out)

    def test_failed_report_is_announced_in_telegram(self):
        sent = []
        config = mock.Mock(bot_token="T", chat_id=42)

        with mock.patch.object(daily, "_run", side_effect=RuntimeError("Yahoo kapalı")), \
                mock.patch.object(daily, "send_telegram", side_effect=lambda *a, **k: sent.append(a)), \
                mock.patch("core.infrastructure.settings.require_bot_settings", return_value=config):
            code = daily.main(["--send"])

        self.assertEqual(code, 1)
        self.assertEqual(len(sent), 1)
        self.assertIn("hazırlanamadı", sent[0][0])
        self.assertIn("Yahoo kapalı", sent[0][0])

    def test_no_notice_without_send(self):
        with mock.patch.object(daily, "_run", side_effect=RuntimeError("x")), \
                mock.patch.object(daily, "send_telegram") as send:
            self.assertEqual(daily.main([]), 1)

        send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
