"""
/tara subscriptions, Aşama 4b (DECISIONS K-42): /tara_abone AD runs a saved screen or a template
after the 18:30 report and sends only the stocks that entered or left (no change, no message); no
run on a holiday or twice on one data day. The file is personal and append-only.
"""

import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from core.market.calendar import ISTANBUL
from core.screen import command, subscriptions
from tests.test_screen import market

NOW = datetime(2026, 10, 28, 20, 0, tzinfo=ISTANBUL)
DAY = date(2026, 10, 28)


class Files(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        d = Path(tmp.name)
        self.paths = dict(path=d / "subs.csv", saved_path=d / "screens.csv")
        self.state = d / "state.json"
        command.save_text(["dusuk", "rsi<30", "ele=hayir"], path=self.paths["saved_path"], now=NOW)

    def sub(self, *words):
        return subscriptions.subscribe_text(list(words), 7, now=NOW, **self.paths)


class CommandsTest(Files):
    def test_subscribe_list_cancel(self):
        self.assertIn("Kullanım", self.sub())
        self.assertIn("kayıtlı tarama ya da şablon yok", self.sub("yok"))
        self.assertIn("Abone olundu: dusuk", self.sub("dusuk"))
        self.assertIn("zaten", self.sub("dusuk"))
        self.assertIn("Abone olundu: duseni_kiran", self.sub("duseni_kiran"))  # a template too
        text = subscriptions.list_text(self.paths["path"])
        self.assertIn("dusuk", text)
        self.assertIn("duseni_kiran", text)
        self.assertIn("18:30", text)
        self.assertIn("İptal edildi: dusuk", subscriptions.cancel_text(["dusuk"], 7, path=self.paths["path"], now=NOW))
        self.assertIn("abone değilsin", subscriptions.cancel_text(["dusuk"], 7, path=self.paths["path"], now=NOW))
        self.assertEqual(list(subscriptions.active(self.paths["path"])), ["duseni_kiran"])

    def test_limit(self):
        for name in list(subscriptions.TEMPLATES)[: subscriptions.MAX_SUBSCRIPTIONS]:
            self.sub(name)
        self.assertIn("En fazla", self.sub("dusuk"))

    def test_append_only(self):
        self.sub("dusuk")
        before = self.paths["path"].read_text(encoding="utf-8")
        subscriptions.cancel_text(["dusuk"], 7, path=self.paths["path"], now=NOW)
        self.assertTrue(self.paths["path"].read_text(encoding="utf-8").startswith(before))

    def test_deleting_the_screen_ends_its_subscription(self):
        self.sub("dusuk")
        with mock.patch.object(subscriptions, "SUBSCRIPTIONS_FILE", self.paths["path"]):
            command.delete_text(["dusuk"], path=self.paths["saved_path"], now=NOW)
        self.assertEqual(subscriptions.active(self.paths["path"]), {})


class RunTest(Files):
    def run_on(self, day, frames, bench):
        return subscriptions.run(day, live=lambda symbols: (frames, bench), state_path=self.state, suspects=set(),
                                 universe_of=lambda q, chat: list(frames), **self.paths)

    def test_only_changes_are_sent(self):
        frames, bench = market()  # S00 and S01 have a low RSI
        self.sub("dusuk")
        first = self.run_on(DAY, frames, bench)
        self.assertEqual(len(first.messages), 1)
        self.assertIn("İlk liste", first.messages[0])
        self.assertIn("S00", first.messages[0])
        self.assertTrue(first.messages[0].rstrip().endswith(command.DISCLAIMER))
        subscriptions.save_state(first, self.state)

        self.assertEqual(self.run_on(date(2026, 10, 29), frames, bench).messages, [])  # nothing changed

        changed = {k: v.copy() for k, v in frames.items()}
        changed["S01.IS"].loc[changed["S01.IS"].index[-5:], ["open", "high", "low", "close"]] *= 1.6  # recovers
        out = self.run_on(date(2026, 10, 30), changed, bench)
        self.assertEqual(len(out.messages), 1)
        self.assertIn("➖ Çıkanlar: S01", out.messages[0])
        self.assertNotIn("➕", out.messages[0])
        for word in ("al ", "sat ", "öneri", "fırsat"):
            self.assertNotIn(word, out.messages[0].replace(command.DISCLAIMER, "").lower())

    def test_a_regime_change_says_why_the_list_emptied(self):
        # öz-denetim 8: rejim= empties the list on another regime's day; the message names it
        frames, bench = market()
        command.save_text(["dusus_rsi", "rsi<30", "ele=hayir", "rejim=dusus"], path=self.paths["saved_path"], now=NOW)
        self.sub("dusus_rsi")
        import pandas as pd

        def regime_is(name):
            return mock.patch("core.market.regime.labels",
                              return_value=pd.Series(name, index=bench.index, dtype=object))

        with regime_is("düşüş"):
            first = self.run_on(DAY, frames, bench)
        subscriptions.save_state(first, self.state)
        with regime_is("yükseliş"):
            out = self.run_on(date(2026, 10, 30), frames, bench)
        self.assertIn("➖ Çıkanlar: S00", out.messages[0])
        self.assertIn("bugünkü rejim yükseliş", out.messages[0])

    def test_same_data_day_twice_runs_once(self):
        frames, bench = market()
        self.sub("dusuk")
        subscriptions.save_state(self.run_on(DAY, frames, bench), self.state)
        frames2 = {k: v.copy() for k, v in frames.items()}
        frames2["S01.IS"]["close"] *= 3
        self.assertEqual(self.run_on(DAY, frames2, bench).messages, [])

    def test_a_changed_criterion_starts_a_new_list(self):
        frames, bench = market()
        self.sub("dusuk")
        subscriptions.save_state(self.run_on(DAY, frames, bench), self.state)
        command.save_text(["dusuk", "rsi<20", "ele=hayir"], path=self.paths["saved_path"], now=NOW)
        out = self.run_on(date(2026, 10, 29), frames, bench)
        self.assertIn("İlk liste", out.messages[0])

    def test_one_failing_screen_does_not_stop_the_others(self):
        frames, bench = market()
        self.sub("dusuk")
        self.sub("bebek_teknik")
        calls = []

        def live(symbols):
            calls.append(1)
            if len(calls) == 1:
                raise OSError("db")
            return frames, bench

        out = subscriptions.run(DAY, live=live, state_path=self.state, suspects=set(),
                                universe_of=lambda q, chat: list(frames), **self.paths)
        self.assertEqual(len(out.messages), 2)
        self.assertTrue(any("çalıştırılamadı" in m for m in out.messages))

    def test_nothing_subscribed(self):
        frames, bench = market()
        self.assertEqual(self.run_on(DAY, frames, bench).messages, [])


class DailyTest(unittest.TestCase):
    """After the 18:30 report, never before it and never on a day that is not sent (holiday)."""

    def run_daily(self, already_sent):
        from core.reports import daily

        fake = daily.DailyResult(DAY, "rapor")
        settings = SimpleNamespace(bot_token="x", chat_id=1)
        sent = []
        with mock.patch.object(daily, "build_daily", return_value=fake), \
                mock.patch.object(daily, "_record_scores", return_value=""), \
                mock.patch.object(daily, "already_sent", return_value=already_sent), \
                mock.patch.object(daily, "_not_sent_reason", return_value=("holiday", "Cumhuriyet Bayramı")), \
                mock.patch.object(daily, "_alarm_hits", return_value=([], None)), \
                mock.patch.object(daily, "_with_backup_line", side_effect=lambda t: t), \
                mock.patch.object(daily, "_with_health_warnings", side_effect=lambda t: t), \
                mock.patch.object(daily, "_with_weekly_line", side_effect=lambda t, d: t), \
                mock.patch.object(daily, "_keep_report_text"), \
                mock.patch("core.infrastructure.settings.require_bot_settings", return_value=settings), \
                mock.patch.object(subscriptions, "run", return_value=subscriptions.Outcome(["değişiklik"], {})) as ran, \
                mock.patch.object(subscriptions, "save_state") as saved, \
                mock.patch.object(daily, "send_telegram", side_effect=lambda t, *a: sent.append(t)):
            result = daily._run_locked(SimpleNamespace(no_update=True, send=True, force=False))
        return result, sent, ran, saved

    def test_after_the_report(self):
        result, sent, ran, saved = self.run_daily(already_sent=False)
        self.assertEqual(sent, ["rapor", "değişiklik"])
        self.assertEqual(ran.call_args.args[0], DAY)
        saved.assert_called_once()
        self.assertEqual(result.status, "sent")

    def test_not_on_a_holiday(self):
        result, sent, ran, _ = self.run_daily(already_sent=True)
        self.assertEqual(sent, [])
        ran.assert_not_called()
        self.assertEqual(result.status, "holiday")

    def test_a_failure_never_touches_the_report(self):
        from core.reports import daily

        with mock.patch.object(subscriptions, "run", side_effect=RuntimeError("x")):
            self.assertEqual(daily._screen_subscriptions(DAY, lambda t: None), None)


class PersonalFileTest(unittest.TestCase):
    def test_backed_up_checked_and_ignored_by_git(self):
        from core import backup
        from core.config.paths import ROOT_DIR, SCREEN_SUBSCRIPTIONS_FILE
        from core.reports import health

        self.assertIn(SCREEN_SUBSCRIPTIONS_FILE, backup.PERSONAL_FILES)
        self.assertIn(SCREEN_SUBSCRIPTIONS_FILE, health.SCHEMAS)
        self.assertIn("data/screen_subscriptions.csv", (ROOT_DIR / ".gitignore").read_text(encoding="utf-8"))

    def test_bot_commands(self):
        from bot.handlers import COMMANDS, MENU
        from bot.start import HELP_TEXT

        for name in ("tara_abone", "tara_abonelikler", "tara_abone_iptal"):
            self.assertIn(name, dict(COMMANDS))
            self.assertIn(name, dict(MENU))
            self.assertIn(f"/{name}", HELP_TEXT)


if __name__ == "__main__":
    unittest.main()
