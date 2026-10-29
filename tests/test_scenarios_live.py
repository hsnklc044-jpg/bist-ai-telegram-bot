"""
Özellik B §4.2: every evening the scenarios that triggered are written to logs/scenarios_log.csv
before their outcome is known (once per day); /performans "Senaryolar" scores them later with the
card's outcome rule. On Fridays the card cache is refreshed after the report.
"""

import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import pandas as pd

from core.analytics import scenarios as S
from tests.test_scenarios import walk


class LogTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "scenarios_log.csv"

    def triggered_frames(self):
        df = walk()
        table = S.signals(df)
        day = next(d for n in S.TEMPLATES for d in table[n].index[table[n]["ok"]])
        return {"AAA.IS": df.loc[:day], "BBB.IS": walk(seed=8).loc[:day]}, day

    def test_written_once_per_day(self):
        frames, day = self.triggered_frames()
        n = S.write_log(day.date(), frames, self.path)
        self.assertGreater(n, 0)
        self.assertEqual(S.write_log(day.date(), frames, self.path), 0)
        rows = pd.read_csv(self.path)
        self.assertEqual(list(rows.columns), S.LOG_COLUMNS)
        self.assertTrue((rows["date"] == day.date().isoformat()).all())
        self.assertTrue(set(rows["template"]) <= set(S.TEMPLATES))

    def test_scored_later_with_the_card_rule(self):
        df = walk(n=400)
        table = S.signals(df)
        name = next(n for n in S.TEMPLATES if table[n]["ok"].iloc[:300].any())
        t = int(table[name]["ok"].to_numpy()[:300].nonzero()[0][0])
        S.write_log(df.index[t].date(), {"AAA.IS": df.iloc[:t + 1]}, self.path)
        lines = S.performance_lines(self.path, bars=lambda s: df)
        expected = S.outcome(df, t, table[name]["invalidation"].iloc[t], table[name]["target"].iloc[t])
        text = "\n".join(lines)
        self.assertIn("🧭 Senaryolar", text)
        self.assertIn(S.TITLES[name], text)
        self.assertIn("veri birikiyor", text)  # one record: no average yet
        self.assertIsNotNone(expected)

    def test_no_log(self):
        text = "\n".join(S.performance_lines(self.path / "yok.csv", bars=lambda s: pd.DataFrame()))
        self.assertIn("Henüz kayıt yok", text)


class DailyTest(unittest.TestCase):
    def test_hooks_never_stop_the_report(self):
        from core.reports import daily

        with mock.patch("core.screen.command._live", side_effect=ValueError("bozuk")):
            daily._record_scenarios(date(2026, 10, 30))  # logged, not raised
        with mock.patch("core.analytics.scenarios_study.study", side_effect=ValueError("bozuk")):
            daily._refresh_scenario_cards(date(2026, 10, 30))  # a Friday

    def test_cards_on_fridays_or_when_missing(self):
        from core.analytics import scenarios_study
        from core.reports import daily

        with mock.patch("core.analytics.scenarios_study.study", return_value={}) as study, \
                mock.patch("core.screen.command._history_data", return_value=None):
            daily._refresh_scenario_cards(date(2026, 10, 29))  # Thursday, no cache yet: computed
            self.assertEqual(study.call_count, 1)
            self.assertTrue(scenarios_study.CARDS_FILE.exists())
            daily._refresh_scenario_cards(date(2026, 10, 29))  # Thursday with a cache: kept
            self.assertEqual(study.call_count, 1)
            daily._refresh_scenario_cards(date(2026, 10, 30))  # Friday: recomputed
            self.assertEqual(study.call_count, 2)

    def test_performance_section(self):
        from core.reports import forward

        with tempfile.TemporaryDirectory() as tmp:
            text = forward.forward_report(Path(tmp) / "s.csv", Path(tmp) / "e.csv", bars=lambda s: pd.DataFrame())
        self.assertIn("🧭 Senaryolar", text)


if __name__ == "__main__":
    unittest.main()
