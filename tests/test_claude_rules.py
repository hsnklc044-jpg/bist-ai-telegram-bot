"""CLAUDE.md, the four skills and the release gate (10.11.2026). CLAUDE.md's hard limits must be the same as
CHARTER's K-54 list; every SKILL.md must be valid; the gate's pure rules are checked with small examples."""

import importlib.util
import re
import unittest
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ("olgunluk", "siradaki-is", "surum-kapisi", "on-kayit")


def gate():
    spec = importlib.util.spec_from_file_location("surum_kapisi", ROOT / "scripts" / "surum_kapisi.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ClaudeMdTest(unittest.TestCase):
    def test_hard_limits_are_the_k54_list(self):
        decisions = (ROOT / "docs" / "DECISIONS.md").read_text(encoding="utf-8")
        k54 = re.search(r"\*\*K-54\..*?yapamayacağım şeylerdir: (.*?)\. Kaynak", decisions, re.S).group(1)
        expected = [item.strip() for item in k54.split(",")]
        text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        section = text.replace("\r\n", "\n").split("## Kesin sınırlar")[1].split("\n\n")[0]
        listed = [ln[2:].strip() for ln in section.splitlines() if ln.startswith("- ")]
        self.assertEqual(listed, expected)

    def test_the_live_folder_rule_and_the_gate_are_named(self):
        text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        for words in (r"C:\Projeler\QuantBIST-yeni", "emir", "surum-kapisi", "on-kayit", "siradaki-is"):
            self.assertIn(words, text)


class SkillFilesTest(unittest.TestCase):
    def test_every_skill_has_a_valid_header(self):
        for name in SKILLS:
            text = (ROOT / ".claude" / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
            head = re.match(r"---\n(.*?)\n---\n", text, re.S)
            self.assertIsNotNone(head, name)
            fields = dict(line.split(":", 1) for line in head.group(1).splitlines())
            self.assertEqual(fields["name"].strip(), name)
            self.assertGreater(len(fields["description"].strip()), 40, name)
            self.assertIn("# ", text[head.end():], name)

    def test_no_skill_touches_the_updater_backup_or_env(self):
        for name in SKILLS:
            text = (ROOT / ".claude" / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
            self.assertNotRegex(text, r"(?i)\.env['\"]?\s*(dosyasını )?(yaz|düzenle|oku)")
            self.assertNotIn("guncelle.py'yi değiştir", text)

    def test_operations_has_the_gate_section(self):
        text = (ROOT / "docs" / "OPERATIONS.md").read_text(encoding="utf-8")
        self.assertIn("## 5a. Sürüm kapısı ve paketleme", text)
        self.assertIn("günde en fazla 4 kurulum", text)


class GateRulesTest(unittest.TestCase):
    def setUp(self):
        self.g = gate()

    def test_the_next_install_skips_the_report_window_and_the_night(self):
        self.assertEqual(self.g.next_install(datetime(2026, 11, 10, 17, 3)), datetime(2026, 11, 10, 17, 40))
        self.assertEqual(self.g.next_install(datetime(2026, 11, 10, 17, 33)), datetime(2026, 11, 10, 20, 40))
        self.assertEqual(self.g.next_install(datetime(2026, 11, 10, 23, 30)), datetime(2026, 11, 11, 7, 40))
        self.assertEqual(self.g.next_install(datetime(2026, 11, 11, 7, 0)), datetime(2026, 11, 11, 7, 40))

    def test_the_window(self):
        ok = self.g.window_ok
        self.assertFalse(ok(datetime(2026, 11, 10, 17, 40), True)[0])  # session
        self.assertFalse(ok(datetime(2026, 11, 10, 18, 40), True)[0])  # report window
        self.assertTrue(ok(datetime(2026, 11, 10, 20, 40), True)[0])
        self.assertTrue(ok(datetime(2026, 11, 11, 7, 40), True)[0])
        self.assertTrue(ok(datetime(2026, 11, 14, 12, 40), False)[0])  # Saturday

    def test_installs_are_version_changes_on_the_day(self):
        log = ["2026-11-09 20:00:00 | INFO | bot.application | QuantBIST v0.99.107 Telegram bot started (x).",
               "2026-11-10 08:00:00 | INFO | bot.application | QuantBIST v0.99.108 Telegram bot started (x).",
               "2026-11-10 09:00:00 | INFO | bot.application | QuantBIST v0.99.108 Telegram bot started (x).",
               "2026-11-10 13:00:00 | INFO | bot.application | QuantBIST v0.99.111 Telegram bot started (x)."]
        self.assertEqual(self.g.installs_on(log, date(2026, 11, 10)), ["0.99.108", "0.99.111"])

    def test_a_worse_slo_is_named(self):
        before = {"A": ["✅", 1.0], "B": ["⚠️", 0.94], "C": ["✅", None]}
        self.assertEqual(self.g.slo_worse(before, {"A": ("✅", 1.0), "B": ("⚠️", 0.95), "C": ("✅", None)}), [])
        worse = self.g.slo_worse(before, {"A": ("❔", None), "B": ("⚠️", 0.93), "C": ("✅", None)})
        self.assertEqual(len(worse), 2)

    def test_live_health_needs_three_beats_and_no_error(self):
        log = ["2026-11-10 17:44:22,404 | INFO | bot.application | QuantBIST v0.99.113 Telegram bot started (x)."]
        beats = [datetime(2026, 11, 10, 17, 45 + 5 * i) for i in range(3)]
        self.assertTrue(self.g.live_health(log, beats, "0.99.113")[0])
        self.assertFalse(self.g.live_health(log, beats[:2], "0.99.113")[0])
        self.assertFalse(self.g.live_health([*log, "2026-11-10 17:50:00,1 | ERROR | x | boom"], beats, "0.99.113")[0])
        self.assertFalse(self.g.live_health(log, beats, "0.99.114")[0])

    def test_updater_backup_and_record_changes_stay_out_of_a_package(self):
        self.assertEqual(self.g.alone_files(["core/reports/slo.py", "scripts/guncelle.py", "core/backup.py"]),
                         ["scripts/guncelle.py", "core/backup.py"])

    def test_the_gate_never_writes_into_the_live_folder(self):
        text = (ROOT / "scripts" / "surum_kapisi.py").read_text(encoding="utf-8")
        self.assertNotIn("--force", text)
        self.assertNotRegex(text, r"LIVE\s*/[^\n]*\.(write_text|write_bytes|open\()")


if __name__ == "__main__":
    unittest.main()
