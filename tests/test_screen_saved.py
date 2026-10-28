"""
Saved screens, Aşama 4 (DECISIONS K-41): /tara_liste lists them, /tara_sil deletes one by adding a
row with empty criteria (the file stays append-only; nothing written before is changed), the same
name can be saved again, and the file survives an upgrade (a file an earlier version wrote reads
the same).
"""

import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from core.market.calendar import ISTANBUL
from core.screen import command

NOW = datetime(2026, 10, 28, 20, 0, tzinfo=ISTANBUL)


class SavedScreensTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "screens.csv"

    def save(self, *words):
        return command.save_text(list(words), path=self.path, now=NOW)

    def test_list(self):
        self.assertIn("Kayıtlı tarama yok", command.list_saved_text(self.path))
        self.save("dusuk_rsi", "rsi<30")
        self.save("trend", "ema20>ema50", "sirala=hacim")
        text = command.list_saved_text(self.path)
        self.assertIn("dusuk_rsi: rsi<30", text)
        self.assertIn("trend: ema20>ema50 sirala=hacim", text)
        self.assertIn("/tara_sil", text)
        self.assertTrue(text.rstrip().endswith(command.DISCLAIMER))

    def test_delete_appends_and_never_rewrites(self):
        self.save("dusuk_rsi", "rsi<30")
        self.save("trend", "ema20>ema50")
        before = self.path.read_text(encoding="utf-8")
        self.assertIn("Silindi: dusuk_rsi", command.delete_text(["dusuk_rsi"], path=self.path, now=NOW))
        self.assertTrue(self.path.read_text(encoding="utf-8").startswith(before))
        self.assertEqual(command.load_saved(self.path), {"trend": "ema20>ema50"})
        self.assertIn("kayıtlı tarama yok", command.delete_text(["dusuk_rsi"], path=self.path, now=NOW))
        self.assertIn("Kaydedildi", self.save("dusuk_rsi", "rsi<25"))  # the name is free again
        self.assertEqual(command.load_saved(self.path)["dusuk_rsi"], "rsi<25")

    def test_wrong_use(self):
        self.assertIn("Kullanım", command.delete_text([], path=self.path))
        self.assertIn("Kullanım", command.delete_text(["a", "b"], path=self.path))
        self.assertIn("şablon", command.delete_text(["duseni_kiran"], path=self.path))

    def test_a_deleted_name_no_longer_runs(self):
        self.save("dusuk_rsi", "rsi<30")
        command.delete_text(["dusuk_rsi"], path=self.path, now=NOW)
        query, answer = command.resolve(["dusuk_rsi"], saved_path=self.path)
        self.assertIsNone(query)  # read as a field name now, and refused
        self.assertIn("dusuk_rsi", answer)

    def test_deleted_screens_do_not_count_against_the_limit(self):
        for i in range(command.MAX_SAVED):
            self.save(f"t{i}", "rsi<30")
        self.assertIn("En fazla", self.save("fazla", "rsi<30"))
        command.delete_text(["t0"], path=self.path, now=NOW)
        self.assertIn("Kaydedildi", self.save("fazla", "rsi<30"))

    def test_file_from_an_earlier_version_reads_the_same(self):
        self.path.write_text("at,name,criteria\n2026-10-27T20:00:00+03:00,eski,rsi<30\n", encoding="utf-8")
        self.assertEqual(command.load_saved(self.path), {"eski": "rsi<30"})
        command.delete_text(["eski"], path=self.path, now=NOW)
        self.assertEqual(self.path.read_text(encoding="utf-8").splitlines()[:2],
                         ["at,name,criteria", "2026-10-27T20:00:00+03:00,eski,rsi<30"])


class BotTest(unittest.TestCase):
    def test_commands(self):
        from bot.handlers import COMMANDS, MENU
        from bot.start import HELP_TEXT

        for name in ("tara_liste", "tara_sil"):
            self.assertIn(name, dict(COMMANDS))
            self.assertIn(name, dict(MENU))
            self.assertIn(f"/{name}", HELP_TEXT)


if __name__ == "__main__":
    unittest.main()
