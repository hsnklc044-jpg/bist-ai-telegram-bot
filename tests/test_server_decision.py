"""
DECISIONS K-23, fixed before any data: the server decision is computed from the SLO records of
02.11–13.11, week by week. A server is recommended only for losses the PC causes (asleep, off,
task not run); Yahoo or Telegram losses do not count, and the targets are never loosened.
"""

import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

from core.market.calendar import ISTANBUL
from core.reports import server_decision as sd


def at(day, hour, minute=0):
    return datetime(2026, 11, day, hour, minute, tzinfo=ISTANBUL)


class Files:
    def __init__(self, case):
        tmp = tempfile.TemporaryDirectory()
        case.addCleanup(tmp.cleanup)
        self.runs = Path(tmp.name) / "runs.csv"
        self.beats = Path(tmp.name) / "heartbeats.csv"
        self.runs.write_text("started_at,finished_at,data_day,status,detail\n", encoding="utf-8")
        self.beats.write_text("at,pid\n", encoding="utf-8")

    def beat_every_5_min(self, start, end, pid=100, skip=None):
        t, lines = start, []
        while t <= end:
            if not (skip and skip[0] <= t < skip[1]):
                lines.append(f"{t.isoformat(timespec='seconds')},{pid}")
            t += timedelta(minutes=5)
        with open(self.beats, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")

    def report(self, day, started=(18, 30), finished=(18, 31), status="sent"):
        with open(self.runs, "a", encoding="utf-8") as fh:
            fh.write(f"{at(day, *started).isoformat()},{at(day, *finished).isoformat()},2026-11-{day:02d},{status},\n")

    def all_reports(self, skip=()):
        for d in range(2, 14):
            if date(2026, 11, d).weekday() < 5 and d not in skip:
                self.report(d)


class DecisionTest(unittest.TestCase):
    def test_a_pc_that_never_sleeps_stays(self):
        f = Files(self)
        f.beat_every_5_min(at(2, 0), at(13, 23, 55))
        f.all_reports()
        result = sd.decide(f.runs, f.beats)
        self.assertFalse(result.server)
        self.assertIn("PC'DE KALINIR", sd.format_decision(result))

    def test_nightly_sleep_recommends_a_server(self):
        f = Files(self)
        for d in range(2, 14):  # asleep 01:00-07:00 every night, same bot process (suspend)
            f.beat_every_5_min(at(d, 0), at(d, 23, 55), skip=(at(d, 1), at(d, 7)))
        f.all_reports()
        result = sd.decide(f.runs, f.beats)
        self.assertTrue(result.server)
        week = result.weeks[0]
        self.assertLess(week.bot, 0.98)
        self.assertGreater(week.sleep, week.down / 2)
        self.assertGreaterEqual(week.long_gaps, 1)
        text = sd.format_decision(result)
        self.assertIn("SUNUCU ÖNERİLİR", text)
        self.assertIn("BENİM ADIMLARIM", text)

    def test_a_pc_switched_off_every_night_counts_too(self):
        """Öz-denetim 4: K-23 says "kapalı/uykuda"; a PC turned off restarts the bot with a new
        process, so a long gap between two processes is the PC as well."""
        f = Files(self)
        for d in range(2, 14):
            f.beat_every_5_min(at(d, 0), at(d, 0, 55), pid=1000 + 2 * d)
            f.beat_every_5_min(at(d, 7), at(d, 23, 55), pid=1001 + 2 * d)
        f.all_reports()
        week = sd.decide(f.runs, f.beats).weeks[0]
        self.assertGreater(week.sleep, week.down / 2)
        self.assertGreaterEqual(week.long_gaps, 1)
        self.assertTrue(sd.decide(f.runs, f.beats).server)

    def test_a_quick_bot_restart_is_not_the_pc(self):
        f = Files(self)
        f.beat_every_5_min(at(2, 0), at(4, 12), pid=1)
        f.beat_every_5_min(at(4, 12, 15), at(13, 23, 55), pid=2)  # crash, task restarted it in minutes
        f.all_reports()
        week = sd.decide(f.runs, f.beats).weeks[0]
        self.assertEqual((week.sleep, week.long_gaps), (sd.timedelta(), 0))
        self.assertFalse(sd.decide(f.runs, f.beats).server)

    def test_a_missed_report_counts_only_when_the_pc_missed_it(self):
        f = Files(self)
        f.beat_every_5_min(at(2, 0), at(13, 23, 55))
        f.all_reports(skip=(4, 5))
        f.report(5, status="stale")  # ran on time, Yahoo had no candle: not the PC
        week = sd.decide(f.runs, f.beats).weeks[0]
        self.assertEqual(week.pc_missed, [date(2026, 11, 4)])
        self.assertEqual(week.other_missed, [date(2026, 11, 5)])
        self.assertTrue(sd.decide(f.runs, f.beats).server)  # 04.11: no run at all, PC was off

    def test_a_late_start_is_the_pc(self):
        f = Files(self)
        f.beat_every_5_min(at(2, 0), at(13, 23, 55))
        f.all_reports(skip=(3,))
        f.report(3, started=(21, 0), finished=(21, 1))  # task caught up after the PC woke up
        self.assertEqual(sd.decide(f.runs, f.beats).weeks[0].pc_missed, [date(2026, 11, 3)])

    def test_before_the_window_ends_it_says_so(self):
        f = Files(self)
        f.beat_every_5_min(at(2, 0), at(5, 12))
        result = sd.decide(f.runs, f.beats, now=at(5, 12))
        text = sd.format_decision(result)
        self.assertIn("penceresi henüz bitmedi", text)
        self.assertNotIn("KARAR", text)  # an interim result is never presented as the decision
        self.assertIn("Ara durum", text)


class ReportLineTest(unittest.TestCase):
    def test_only_on_the_last_day_of_the_window(self):
        self.assertTrue(sd.due(date(2026, 11, 13)))
        self.assertFalse(sd.due(date(2026, 11, 6)))


    def test_the_13_11_report_carries_it(self):
        from unittest import mock

        from core.reports import daily

        with mock.patch.object(daily, "now_istanbul", return_value=at(13, 18, 30)):
            text = daily._with_weekly_line(f"rapor\n\n{daily.DISCLAIMER}", date(2026, 11, 13))
            other = daily._with_weekly_line(f"rapor\n\n{daily.DISCLAIMER}", date(2026, 11, 6))
        self.assertIn("Sunucu kararı", text)
        self.assertNotIn("Sunucu kararı", other)
        self.assertTrue(text.rstrip().endswith(daily.DISCLAIMER))


if __name__ == "__main__":
    unittest.main()
