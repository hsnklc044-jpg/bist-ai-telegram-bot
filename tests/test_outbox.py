"""Copy of every outgoing Telegram message (logs/telegram_giden.jsonl), 10.11.2026 user request.
Written before the code: a failed send is recorded too; token, chat_id and monitoring addresses never reach the
file; the file only grows; lines older than 30 days move to a monthly archive, never deleted."""

import asyncio
import json
import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest import mock

import pytest

from core.infrastructure import outbox
from core.market.calendar import ISTANBUL

NOW = datetime(2026, 11, 10, 20, 0, tzinfo=ISTANBUL)
# built at run time so the repository secret scan (test_repo_secrets) never sees a token-shaped literal
TOKEN = "123456789:" + "AA" + "Hfake" * 6 + "-xyz"
CHAT = 987654321
HC = "https://hc-ping.com/" + "-".join(["0f1e2d3c", "aaaa", "bbbb", "cccc", "1234567890ab"])


@pytest.fixture(autouse=True)
def _tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(outbox, "OUTBOX_FILE", tmp_path / "telegram_giden.jsonl")
    monkeypatch.setenv("BOT_TOKEN", TOKEN)
    monkeypatch.setenv("CHAT_ID", str(CHAT))
    monkeypatch.setenv("HC_BOT_URL", HC)


def rows():
    return [json.loads(line) for line in outbox.OUTBOX_FILE.read_text(encoding="utf-8").splitlines()]


class RecordTest(unittest.TestCase):
    def test_a_line_per_message_with_time_source_result_and_text(self):
        outbox.record("bot", "merhaba", True, now=NOW)
        outbox.record("günlük rapor", "rapor metni", False, now=NOW + timedelta(minutes=1))
        got = rows()
        self.assertEqual([r["kaynak"] for r in got], ["bot", "günlük rapor"])
        self.assertEqual([r["sonuc"] for r in got], ["gönderildi", "başarısız"])
        self.assertEqual(got[0]["metin"], "merhaba")
        self.assertEqual(got[0]["zaman"], "2026-11-10T20:00:00+03:00")
        self.assertEqual(set(got[0]), {"zaman", "kaynak", "sonuc", "metin"})

    def test_secrets_never_reach_the_file(self):
        text = (f"token {TOKEN} sohbet {CHAT} izleme {HC} "
                f"https://api.telegram.org/bot{TOKEN}/sendMessage başka 555666777:BBBotherOTHERother_token-ZZZZZZZZZZ")
        outbox.record("bot", text, True, now=NOW)
        raw = outbox.OUTBOX_FILE.read_text(encoding="utf-8")
        for secret in (TOKEN, str(CHAT), HC, "hc-ping.com/0f1e", "555666777:BBB", "api.telegram.org/bot"):
            self.assertNotIn(secret, raw)
        self.assertIn("[gizli]", raw)

    def test_the_file_only_grows(self):
        outbox.record("bot", "bir", True, now=NOW)
        before = outbox.OUTBOX_FILE.read_bytes()
        outbox.record("bot", "iki", True, now=NOW)
        self.assertTrue(outbox.OUTBOX_FILE.read_bytes().startswith(before))

    def test_a_broken_disk_never_stops_a_message(self):
        with mock.patch("builtins.open", side_effect=OSError("disk dolu")):
            outbox.record("bot", "x", True, now=NOW)  # no exception


class ArchiveTest(unittest.TestCase):
    def test_lines_older_than_30_days_move_to_a_monthly_archive_never_deleted(self):
        for days, text in ((45, "eski ekim"), (31, "eski ekim 2"), (29, "yeni"), (0, "bugün")):
            outbox.record("bot", text, True, now=NOW - timedelta(days=days), archive=False)
        moved = outbox.archive(NOW)
        self.assertEqual(moved, 2)
        self.assertEqual([r["metin"] for r in rows()], ["yeni", "bugün"])
        october = outbox.OUTBOX_FILE.with_name("telegram_giden_2026-09.jsonl")
        archived = [json.loads(x)["metin"] for x in october.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(archived, ["eski ekim"])
        october2 = outbox.OUTBOX_FILE.with_name("telegram_giden_2026-10.jsonl")
        self.assertEqual([json.loads(x)["metin"] for x in october2.read_text(encoding="utf-8").splitlines()],
                         ["eski ekim 2"])
        self.assertEqual(outbox.archive(NOW), 0)  # nothing twice

    def test_an_archive_that_exists_is_appended_to(self):
        outbox.record("bot", "a", True, now=NOW - timedelta(days=40), archive=False)
        outbox.archive(NOW)
        outbox.record("bot", "b", True, now=NOW - timedelta(days=40), archive=False)
        outbox.archive(NOW)
        month = outbox.OUTBOX_FILE.with_name("telegram_giden_2026-10.jsonl")
        self.assertEqual([json.loads(x)["metin"] for x in month.read_text(encoding="utf-8").splitlines()], ["a", "b"])


class WiringTest(unittest.TestCase):
    def test_the_daily_sender_records_each_part_also_when_it_fails(self):
        from core.reports import daily

        ok = SimpleNamespace(status_code=200, raise_for_status=lambda: None)
        daily.send_telegram("rapor", TOKEN, CHAT, post=lambda *a, **k: ok, sleep=lambda s: None)

        def down(*a, **k):
            raise ConnectionError("yok")

        with self.assertRaises(ConnectionError):
            daily.send_telegram("ikinci", TOKEN, CHAT, post=down, sleep=lambda s: None, source="güncelleyici")
        got = rows()
        self.assertEqual([(r["kaynak"], r["sonuc"], r["metin"]) for r in got],
                         [("günlük rapor", "gönderildi", "rapor"), ("güncelleyici", "başarısız", "ikinci")])

    def test_the_bot_records_replies_and_job_messages_with_their_source(self):
        from bot.application import RecordingBot

        sent = []

        async def fake_send(self, chat_id, text, *args, **kwargs):
            sent.append(text)
            if text == "hata":
                raise RuntimeError("telegram")
            return "ok"

        with mock.patch("telegram.ext.ExtBot.send_message", fake_send):
            bot = RecordingBot(token=TOKEN)
            asyncio.run(bot.send_message(CHAT, "yanıt"))
            with outbox.source("robot özeti"):
                asyncio.run(bot.send_message(CHAT, "özet"))
            with self.assertRaises(RuntimeError):
                asyncio.run(bot.send_message(CHAT, "hata"))
        got = [(r["kaynak"], r["sonuc"], r["metin"]) for r in rows()]
        self.assertEqual(got, [("bot", "gönderildi", "yanıt"), ("robot özeti", "gönderildi", "özet"),
                               ("bot", "başarısız", "hata")])

    def test_the_jobs_tag_their_messages(self):
        import inspect

        from bot import scheduler

        source = inspect.getsource(scheduler)
        self.assertEqual(source.count('outbox.source("sağlık uyarısı")'), 2)
        self.assertEqual(source.count('outbox.source("robot özeti")'), 1)

    def test_the_bot_is_built_with_the_recording_bot_and_the_usual_pool(self):
        from bot import application

        bot = application._bot(TOKEN)
        self.assertIsInstance(bot, application.RecordingBot)
        self.assertEqual(bot._request[1]._client_kwargs["limits"].max_connections, 256)


if __name__ == "__main__":
    unittest.main()
