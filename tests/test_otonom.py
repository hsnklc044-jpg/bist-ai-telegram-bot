"""/otonom_dur, /otonom_devam and the 21:00 summary (10.11.2026)."""

import asyncio
import json
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest import mock

import pytest

from core import otonom
from core.market.calendar import ISTANBUL

NOW = datetime(2026, 11, 10, 21, 0, tzinfo=ISTANBUL)  # Tuesday
LOG = ["2026-11-09 20:00:00,1 | INFO | bot.application | QuantBIST v0.99.112 Telegram bot started (x).",
       "2026-11-10 08:00:00,1 | INFO | bot.application | QuantBIST v0.99.112 Telegram bot started (x).",
       "2026-11-10 17:44:22,4 | INFO | bot.application | QuantBIST v0.99.113 Telegram bot started (x).",
       "2026-11-10 20:44:10,1 | INFO | bot.application | QuantBIST v0.99.114 Telegram bot started (x)."]
CHANGELOG = ("## v0.99.114 – 10.11.2026 (/uzun_liste: 6–12 ay modeli BIST 100 sıralaması)\n- x\n"
             "## v0.99.113 – 10.11.2026 (üst alım fiyatı kalıcı kayıt: /uzun_ust)\n")
SLO = [SimpleNamespace(state="✅", name="Rapor teslimi"), SimpleNamespace(state="⚠️", name="Bot ayakta kalma")]


@pytest.fixture(autouse=True)
def _tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(otonom, "STOP_FILE", tmp_path / "otonom_dur.flag")
    monkeypatch.setattr(otonom, "TOOLS_DIR", tmp_path / "araclar")


class FlagTest(unittest.TestCase):
    def test_stop_writes_the_flag_once_and_resume_lifts_both(self):
        self.assertEqual(otonom.stopped(), [])
        self.assertIn("durduruldu", otonom.stop(NOW))
        self.assertTrue(otonom.STOP_FILE.exists())
        self.assertIn("kullanıcı /otonom_dur", otonom.STOP_FILE.read_text(encoding="utf-8"))
        self.assertIn("zaten durdurulmuş", otonom.stop(NOW))
        otonom.brake_file().parent.mkdir(parents=True)
        otonom.brake_file().write_text("fren: aynı gün 2 geri dönüş", encoding="utf-8")
        self.assertEqual(len(otonom.stopped()), 2)
        text = otonom.resume()
        self.assertIn("yeniden açık", text)
        self.assertIn("fren: aynı gün 2 geri dönüş", text)
        self.assertEqual(otonom.stopped(), [])
        self.assertIn("zaten açık", otonom.resume())

    def test_the_commands_are_registered_and_documented(self):
        from bot.handlers import COMMANDS, MENU
        from bot.start import HELP_TEXT

        for name in ("otonom_dur", "otonom_devam"):
            self.assertIn(name, dict(COMMANDS))
            self.assertIn(name, dict(MENU))
            self.assertIn(f"/{name}", HELP_TEXT)

    def test_the_command_answers(self):
        from bot import control
        from tests.test_screen_telegram import fake_update

        sent = []
        asyncio.run(control.otonom_stop_cmd(fake_update(sent), SimpleNamespace(args=[])))
        asyncio.run(control.otonom_resume_cmd(fake_update(sent), SimpleNamespace(args=[])))
        self.assertIn("durduruldu", sent[0][0])
        self.assertIn("yeniden açık", sent[1][0])


class SummaryTest(unittest.TestCase):
    def test_installs_titles_slos_and_the_record(self):
        record = {"day": "2026-11-10", "branches": {"0.99.114": ["uzun-liste"]},
                  "ci": {"0.99.114": "https://github.com/x/actions/runs/1"}, "rollbacks": 0,
                  "maturity": {"S2": 62}, "next": "slo-kirpma paketi 07:40"}
        text = otonom.summary_text(NOW, LOG, CHANGELOG, SLO, record)
        self.assertIn("yalnız bilgi", text)
        self.assertIn("• v0.99.113 (17:44): üst alım fiyatı kalıcı kayıt: /uzun_ust", text)
        self.assertIn("• v0.99.114 (20:44): /uzun_liste", text)
        self.assertIn("dallar: uzun-liste · CI: https://github.com/x/actions/runs/1", text)
        self.assertIn("Geri dönüş: 0", text)
        self.assertIn("✅ Rapor teslimi · ⚠️ Bot ayakta kalma", text)
        self.assertIn("Olgunluk: S2 %62", text)
        self.assertIn("Yarın sıradaki iş: slo-kirpma paketi 07:40", text)
        self.assertNotIn("?", text.replace("https://", ""))  # information, never a question
        self.assertNotIn("Haftalık SLO tablosu", text)

    def test_a_quiet_day_a_stop_flag_and_saturday(self):
        otonom.stop(NOW)
        saturday = datetime(2026, 11, 14, 21, 0, tzinfo=ISTANBUL)
        with mock.patch("core.reports.slo.lines", return_value=["✅ Rapor teslimi: 100%"]):
            text = otonom.summary_text(saturday, LOG, CHANGELOG, SLO, None)
        self.assertIn("Bugün kurulum yok.", text)
        self.assertIn("Durdurma bayrağı açık", text)
        self.assertIn("Haftalık SLO tablosu", text)
        self.assertIn("Yarın sıradaki iş: kayıt yok", text)

    def test_an_old_record_is_not_shown_as_today(self):
        otonom.day_file().parent.mkdir(parents=True)
        otonom.day_file().write_text(json.dumps({"day": "2026-11-09", "rollbacks": 3, "next": "x"}), encoding="utf-8")
        with mock.patch("core.reports.slo.measure", return_value=SLO), \
                mock.patch.object(otonom, "LOG_DIR", otonom.TOOLS_DIR):
            text = otonom.build_summary(NOW)
        self.assertIn("Geri dönüş: 0", text)
        self.assertIn("Yarın sıradaki iş: x", text)

    def test_the_job_is_scheduled_at_21(self):
        from bot import scheduler

        app = SimpleNamespace(job_queue=mock.Mock())
        self.assertTrue(scheduler.schedule_otonom_summary(app, 42))
        kwargs = app.job_queue.run_daily.call_args.kwargs
        self.assertEqual((kwargs["time"].hour, kwargs["time"].minute, kwargs["chat_id"]), (21, 0, 42))
        self.assertFalse(scheduler.schedule_otonom_summary(app, None))


if __name__ == "__main__":
    unittest.main()
