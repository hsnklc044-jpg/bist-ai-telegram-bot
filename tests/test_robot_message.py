"""The 21:00 robot summary in the message style (H, the user's 11.11.2026 decision). Written before the code.

No problem: three lines ("ROBOT · date", "✅ N güncelleme sorunsuz kuruldu", "Yarın: …"). Problems: the status, the
problems in plain words, "Senden beklenen:" when something is expected, "/robot_detay"; at most six lines. Versions,
links and the queue move to /robot_detay. No internal codes in the message."""

import asyncio
import json
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest import mock

import pytest

from core import otonom
from core.market.calendar import ISTANBUL
from core.reports import style

NOW = datetime(2026, 11, 11, 21, 0, tzinfo=ISTANBUL)
LOG = ["2026-11-10 20:44:10,1 | INFO | bot.application | QuantBIST v0.99.114 Telegram bot started (x).",
       "2026-11-11 07:45:09,1 | INFO | bot.application | QuantBIST v0.99.119 Telegram bot started (x).",
       "2026-11-11 08:46:32,1 | INFO | bot.application | QuantBIST v0.99.122 Telegram bot started (x)."]
GOOD = [SimpleNamespace(state="✅", name="Rapor teslimi"), SimpleNamespace(state="❔", name="Veri doğruluğu")]
BAD = [SimpleNamespace(state="⚠️", name="Bot ayakta kalma"), SimpleNamespace(state="🛑", name="Yedek")]


@pytest.fixture(autouse=True)
def _tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(otonom, "STOP_FILE", tmp_path / "otonom_dur.flag")
    monkeypatch.setattr(otonom, "TOOLS_DIR", tmp_path / "araclar")


class ShortTest(unittest.TestCase):
    def test_a_quiet_day_is_three_lines(self):
        text = otonom.short_text(NOW, LOG, GOOD, {"next": "resmî endeks verisi"}, checks=["✅ Dallar: 22 aynı"])
        self.assertEqual(text.splitlines(), ["ROBOT · 11.11.2026", "✅ 2 güncelleme sorunsuz kuruldu",
                                             "Yarın: resmî endeks verisi"])
        self.assertEqual(style.problems(text, "robot"), [])

    def test_no_install_no_problem(self):
        text = otonom.short_text(NOW, [], GOOD, None)
        self.assertEqual(text.splitlines()[1], "✅ Bugün güncelleme yok; her şey yolunda")

    def test_problems_in_plain_words_with_the_detail_command(self):
        otonom.stop(NOW)
        text = otonom.short_text(NOW, LOG, BAD, {"rollbacks": 1, "expect": "dal kararını yaz"},
                                 checks=["⚠️ Dallar: 22 dalın 1'i farklı"])
        lines = text.splitlines()
        self.assertEqual(lines[0], "ROBOT · 11.11.2026")
        self.assertTrue(lines[1].startswith("⚠️ "))
        self.assertIn("Senden beklenen: dal kararını yaz", lines)
        self.assertEqual(lines[-1], "/robot_detay")
        self.assertLessEqual(len(lines), 6)
        self.assertEqual(style.problems(text, "robot", sorun=True), [])
        self.assertNotIn("🛑", text)

    def test_versions_and_links_stay_in_the_detail(self):
        record = {"ci": {"0.99.119": "https://github.com/x/actions/runs/1"}, "next": "x"}
        short = otonom.short_text(NOW, LOG, GOOD, record)
        detail = otonom.summary_text(NOW, LOG, "", GOOD, record)
        self.assertNotIn("v0.99", short)
        self.assertNotIn("https://", short)
        self.assertIn("v0.99.119", detail)
        self.assertIn("https://github.com/x/actions/runs/1", detail)


class WiringTest(unittest.TestCase):
    def test_the_job_sends_the_short_text_and_robot_detay_the_detail(self):
        otonom.day_file().parent.mkdir(parents=True)
        otonom.day_file().write_text(json.dumps({"day": "2026-11-11", "next": "x"}), encoding="utf-8")
        with mock.patch("core.reports.slo.measure", return_value=GOOD), \
                mock.patch.object(otonom, "LOG_DIR", otonom.TOOLS_DIR), \
                mock.patch.object(otonom, "branches_line", return_value="✅ Dallar: 1"), \
                mock.patch.object(otonom, "outside_copy_line", return_value="✅ Depo dışı: 1"):
            short = otonom.build_summary(NOW)
            detail = otonom.build_detail(NOW)
        self.assertTrue(short.startswith("ROBOT · 11.11.2026"))
        self.assertIn("Otonom günlük özet", detail)

    def test_robot_detay_is_registered_and_answers(self):
        from bot import control
        from bot.handlers import COMMANDS, MENU
        from bot.start import HELP_TEXT
        from tests.test_screen_telegram import fake_update

        self.assertIn("robot_detay", dict(COMMANDS))
        self.assertIn("robot_detay", dict(MENU))
        self.assertIn("/robot_detay", HELP_TEXT)
        sent = []
        with mock.patch.object(otonom, "build_detail", return_value="ayrıntı"):
            asyncio.run(control.robot_detail_cmd(fake_update(sent), SimpleNamespace(args=[])))
        self.assertEqual(sent[0][0], "ayrıntı")


if __name__ == "__main__":
    unittest.main()
