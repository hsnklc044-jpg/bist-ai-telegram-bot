"""
Closing price alarms (core/alerts/levels.py): the user sets a level, the evening report says when
a stock closed beyond it, once. Daily closes only: no intraday alarm. The file is append-only
(set, removed and triggered are new rows; no row is ever rewritten), like the ledger.
"""

import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock

from core.alerts import levels
from core.market.calendar import ISTANBUL

NOW = datetime(2026, 10, 28, 20, 0, tzinfo=ISTANBUL)
DAY = date(2026, 10, 28)


class AlarmFileTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "price_alarms.csv"

    def test_set_list_remove_and_the_file_only_grows(self):
        a = levels.add("thyao", "below", 240, path=self.path, now=NOW)
        b = levels.add("EREGL.IS", "above", 45.5, path=self.path, now=NOW)
        self.assertEqual((a.id, a.symbol, b.id), (1, "THYAO.IS", 2))
        self.assertEqual([x.id for x in levels.active(self.path)], [1, 2])
        before = self.path.read_text(encoding="utf-8")
        self.assertTrue(levels.remove(1, path=self.path, now=NOW))
        self.assertFalse(levels.remove(1, path=self.path, now=NOW))  # already removed
        self.assertFalse(levels.remove(99, path=self.path, now=NOW))
        self.assertTrue(self.path.read_text(encoding="utf-8").startswith(before))  # nothing rewritten
        self.assertEqual([x.id for x in levels.active(self.path)], [2])

    def test_triggers_once_on_the_close_and_writes_it(self):
        levels.add("THYAO", "below", 240, path=self.path, now=NOW)
        levels.add("EREGL", "above", 50, path=self.path, now=NOW)
        levels.add("BIMAS", "below", 400, path=self.path, now=NOW)
        hits = levels.check(DAY, {"THYAO.IS": 238.5, "EREGL.IS": 49.0}, path=self.path, now=NOW)
        self.assertEqual([(h.alarm.symbol, h.close) for h in hits], [("THYAO.IS", 238.5)])  # BIMAS: no close today
        self.assertEqual(levels.check(DAY, {"THYAO.IS": 230.0}, path=self.path, now=NOW), [])  # once
        self.assertEqual([x.symbol for x in levels.active(self.path)], ["EREGL.IS", "BIMAS.IS"])
        line = levels.format_hits(hits)
        self.assertIn("🔔 THYAO 238,50 ile 240,00'ın altında kapandı", line)

    def test_check_without_writing(self):
        levels.add("THYAO", "below", 240, path=self.path, now=NOW)
        self.assertEqual(len(levels.check(DAY, {"THYAO.IS": 200.0}, path=self.path, now=NOW, write=False)), 1)
        self.assertEqual(len(levels.active(self.path)), 1)

    def test_bad_input_is_refused(self):
        for symbol, direction, level in (("THYAO", "below", 0), ("THYAO", "yukarı", 10), ("../x", "below", 10)):
            with self.subTest(symbol=symbol, direction=direction, level=level), self.assertRaises(ValueError):
                levels.add(symbol, direction, level, path=self.path, now=NOW)


class CommandTextTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "price_alarms.csv"

    def run_words(self, *words):
        return levels.command(list(words), path=self.path, now=NOW)

    def test_command_words(self):
        self.assertIn("Kurulu alarm yok", self.run_words())
        self.assertIn("#1 THYAO kapanış 240,50'ın altına inerse", self.run_words("THYAO", "altında", "240,5"))
        self.assertIn("#2 EREGL kapanış 50,00'ın üstüne çıkarsa", self.run_words("eregl", "üstünde", "50"))
        listing = self.run_words()
        self.assertIn("#1 THYAO", listing)
        self.assertIn("yalnız akşam kapanışında", listing)
        self.assertIn("silindi", self.run_words("sil", "1"))
        self.assertIn("bulunamadı", self.run_words("sil", "1"))
        self.assertIn("Kullanım", self.run_words("THYAO", "240"))
        self.assertIn("Kullanım", self.run_words("THYAO", "altında", "dün"))


class DailyReportTest(unittest.TestCase):
    """The evening report names a crossed alarm and marks it only after the report went out."""

    def setUp(self):
        import pandas as pd

        from core.reports import daily

        levels.add("THYAO", "below", 240, now=NOW)
        frame = pd.DataFrame({"close": [250.0, 238.0]}, index=pd.to_datetime(["2026-10-27", "2026-10-28"]))
        patcher = mock.patch.object(daily, "raw_bars", return_value=frame)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_line_and_mark(self):
        from core.reports import daily

        hits, line = daily._alarm_hits(DAY)
        self.assertIn("🔔 THYAO 238,00 ile 240,00'ın altında kapandı", line)
        self.assertEqual(len(levels.active()), 1)  # not written yet
        daily._mark_alarms(hits)
        self.assertEqual(levels.active(), [])
        self.assertEqual(daily._alarm_hits(DAY), ([], None))

    def test_alarm_stocks_are_updated(self):
        from core.reports import daily

        self.assertIn("THYAO.IS", daily._alarm_symbols())

    def test_damaged_file_never_stops_the_report(self):
        from core.reports import daily

        levels.PRICE_ALARMS_FILE.write_text("", encoding="utf-8")
        hits, line = daily._alarm_hits(DAY)
        self.assertEqual(hits, [])
        self.assertIn("kontrol edilemedi", line)
        self.assertEqual(daily._alarm_symbols(), [])


class BotCommandTest(unittest.TestCase):
    def test_alarm_command_is_wired(self):
        from bot.handlers import COMMANDS, MENU
        from tests.test_bot_handlers import run

        self.assertIn("alarm", dict(COMMANDS))
        self.assertIn("alarm", dict(MENU))
        out = run(dict(COMMANDS)["alarm"], ["THYAO", "üstünde", "300"])
        self.assertIn("Alarm kuruldu", "".join(out))


if __name__ == "__main__":
    unittest.main()
