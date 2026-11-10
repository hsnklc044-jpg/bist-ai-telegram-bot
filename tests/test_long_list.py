"""/uzun_liste: the 6-12 month model over a list of stocks, the decision kept apart from the score."""

import asyncio
import unittest
from types import SimpleNamespace
from unittest import mock

from core.analytics import long_model as M
from core.market.calendar import ISTANBUL  # noqa: F401  (keeps the import graph the same as the other model tests)
from tests.test_long_model import breakout_frame
from tests.test_scorecard import bars, trend


def frames():
    return {"AAA.IS": trend(400), "BBB.IS": breakout_frame(), "CCC.IS": bars(120),
            "DDD.IS": trend(400, growth=0.997, volume_growth=False)}


class RankTest(unittest.TestCase):
    def test_entry_candidates_first_then_watch_by_score_then_missing_data(self):
        items = M.rank(frames(), uppers={"BBB.IS": 1e9})
        order = [s for s, _ in items]
        self.assertEqual(order[0], "BBB.IS")
        self.assertEqual(items[0][1].status, M.ENTER)
        self.assertEqual(order[-1], "CCC.IS")
        self.assertEqual(items[-1][1].status, M.LACKING)
        watch = [r.card.total for _, r in items if r.status == M.WATCH]
        self.assertEqual(watch, sorted(watch, reverse=True))

    def test_a_high_score_is_not_a_candidate_by_itself(self):
        items = M.rank({"AAA.IS": trend(400)}, uppers={"AAA.IS": 1e9})
        self.assertGreaterEqual(items[0][1].card.total, 80)
        self.assertEqual(items[0][1].status, M.WATCH)  # no breakout, no relative volume

    def test_ties_go_by_code(self):
        same = trend(400)
        order = [s for s, _ in M.rank({"ZZZ.IS": same, "AAA.IS": same, "MMM.IS": same})]
        self.assertEqual(order, ["AAA.IS", "MMM.IS", "ZZZ.IS"])

    def test_empty_frames_are_skipped(self):
        import pandas as pd

        self.assertEqual(M.rank({"AAA.IS": pd.DataFrame(), "BBB.IS": None}), [])


class TextTest(unittest.TestCase):
    def test_lines_show_the_four_conditions_and_the_saved_count(self):
        items = M.rank(frames(), uppers={"BBB.IS": 1e9})
        text = M.ranking_text(items, limit=15, saved=1)
        lines = text.splitlines()
        self.assertIn("100", lines[0].replace("4 hisse", "100"))  # header present
        self.assertIn("Giriş adayı: 1", lines[0])
        self.assertIn("Veri yetersiz: 1", lines[0])
        self.assertRegex(lines[1], r"^1\. BBB · \d+/100 · Giriş adayı — SMA trendi ✅ · kırılım ✅ · hacim ✅ · üst alım ✅")
        self.assertIn("üst alım ❔", text)  # AAA has no saved price
        self.assertIn("CCC · 0/100 · Veri yetersiz — veri yok", text)
        self.assertIn("kayıtlı üst alım fiyatı: 1/4", text)
        self.assertIn("öneri değildir", text)
        for word in (" al ", " sat ", "fırsat"):
            self.assertNotIn(word, text.lower())

    def test_a_price_under_the_close_marks_the_cap_condition_failed(self):
        items = M.rank({"BBB.IS": breakout_frame()}, uppers={"BBB.IS": 1.0})
        self.assertIn("üst alım ❌", M.ranking_text(items))
        self.assertEqual(items[0][1].status, M.WATCH)

    def test_the_limit_is_clamped_and_the_rest_is_counted(self):
        many = {f"S{i:02d}.IS": trend(400) for i in range(40)}
        items = M.rank(many)
        self.assertEqual(len(M.ranking_text(items, limit=0).splitlines()), 1 + 1 + 1 + 1)  # head, 1 row, "ve N", footer
        text = M.ranking_text(items, limit=99)
        self.assertEqual(len(text.splitlines()), 1 + M.MAX_LIST + 1 + 1)
        self.assertIn(f"ve {40 - M.MAX_LIST} hisse daha", text)
        self.assertIn(f"/uzun_liste {M.MAX_LIST}", M.ranking_text(items, limit=1))


class CommandTest(unittest.TestCase):
    def run_command(self, args, **patches):
        import contextlib

        from bot import analysis
        from tests.test_screen_telegram import fake_update

        sent = []
        base = {"core.reports.daily.adjusted_bars": dict(side_effect=lambda s: frames()[s]),
                "core.screen.universe.symbols": dict(return_value=list(frames())),
                "core.market.upper_buy.load": dict(return_value={"BBB.IS": (1e9, "2026-11-10")})}
        base.update(patches)
        with contextlib.ExitStack() as stack:
            for target, kw in base.items():
                stack.enter_context(mock.patch(target, **kw))
            asyncio.run(analysis.long_list_cmd(fake_update(sent), SimpleNamespace(args=args)))
        return sent[0][0]

    def test_registered_and_documented(self):
        from bot.handlers import COMMANDS, MENU
        from bot.start import HELP_TEXT

        self.assertIn("uzun_liste", dict(COMMANDS))
        self.assertIn("uzun_liste", dict(MENU))
        self.assertIn("/uzun_liste", HELP_TEXT)

    def test_default_and_a_count(self):
        text = self.run_command([])
        self.assertIn("1. BBB", text)
        self.assertIn("Giriş adayı: 1", text)
        self.assertEqual(len([ln for ln in self.run_command(["2"]).splitlines() if ln[:2] in ("1.", "2.", "3.")]), 2)

    def test_bad_arguments_get_the_usage(self):
        for args in (["x"], ["0"], ["31"], ["1", "2"]):
            self.assertIn("Kullanım", self.run_command(args), args)

    def test_an_unreadable_saved_file_is_said_and_the_list_still_comes(self):
        from pathlib import Path

        from core.infrastructure.exceptions import PersonalFileError

        text = self.run_command([], **{"core.market.upper_buy.load": dict(
            side_effect=PersonalFileError(Path("upper_buy.csv"), "3. satır: fiyat sayı değil"))})
        self.assertIn("Kayıtlı üst alım fiyatları okunamadı", text)
        self.assertIn("Giriş adayı: 0", text)

    def test_no_data_and_a_failure_are_said(self):
        self.assertIn("fiyat verisi yok", self.run_command([], **{"core.reports.daily.adjusted_bars": dict(return_value=None)}))
        self.assertIn("hazırlanamadı", self.run_command([], **{"core.screen.universe.symbols": dict(side_effect=OSError("x"))}))


if __name__ == "__main__":
    unittest.main()
