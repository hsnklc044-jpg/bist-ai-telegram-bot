"""
Dividend and corporate event calendar (road plan part 2): the user's own entries (no automated
access to KAP, K-48), append-only, for the stocks they hold or watch.
"""

import tempfile
import unittest
from datetime import date
from pathlib import Path

from core.reports import events as E


class EventsTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "events.csv"
        self.today = date(2026, 11, 5)

    def cmd(self, *words, held=("THYAO.IS",), watched=()):
        return E.command_text(list(words), self.path, self.today, held=set(held), watched=set(watched))

    def test_add_list_and_delete(self):
        self.assertIn("Eklendi #1", self.cmd("ekle", "THYAO", "05.12.2026", "temettü", "3,25", "TL", "brüt"))
        self.assertIn("Eklendi #2", self.cmd("ekle", "ASELS", "2026-11-20", "genel", "kurul"))
        text = self.cmd()
        self.assertIn("THYAO 05.12.2026 (30 gün sonra): temettü 3,25 TL brüt [portföyde]", text)
        self.assertNotIn("ASELS", text)  # neither held nor watched
        self.assertIn("ASELS", self.cmd("hepsi"))
        self.assertIn("Silindi #1", self.cmd("sil", "1"))
        self.assertNotIn("THYAO", self.cmd("hepsi"))
        self.assertEqual(len(self.path.read_text(encoding="utf-8").splitlines()), 4)  # header, 2 adds, 1 delete

    def test_window_and_past(self):
        self.cmd("ekle", "THYAO", "01.11.2026", "temettü")   # past
        self.cmd("ekle", "THYAO", "01.03.2027", "temettü")   # beyond 30 days
        self.cmd("ekle", "THYAO", "10.11.2026", "bölünme", "2:1")
        text = self.cmd()
        self.assertIn("10.11.2026", text)
        self.assertNotIn("01.11.2026", text)
        self.assertNotIn("01.03.2027", text)

    def test_errors(self):
        for words in (["ekle", "THYAO"], ["ekle", "THYAO", "32.13.2026", "x"], ["ekle", "A", "05.12.2026", "x"],
                      ["sil", "9"], ["sil", "x"], ["bilinmeyen"]):
            self.assertIn("⚠️", self.cmd(*words), words)

    def test_upcoming_for_the_health_report(self):
        self.cmd("ekle", "THYAO", "10.11.2026", "temettü")
        lines = E.upcoming_lines(self.path, self.today, {"THYAO.IS"})
        self.assertEqual(len(lines), 1)
        self.assertIn("THYAO", lines[0])

    def test_personal_file_is_protected(self):
        from core.backup import PERSONAL_FILES
        from core.config.paths import DATA_DIR

        self.assertIn(DATA_DIR / "events.csv", PERSONAL_FILES)  # (tests point EVENTS_FILE to a temp folder)
        ignored = (Path(__file__).resolve().parents[1] / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("data/events.csv", ignored)

    def test_command_registered(self):
        from bot import handlers

        self.assertIn("takvim", [name for name, _ in handlers.COMMANDS])


if __name__ == "__main__":
    unittest.main()
