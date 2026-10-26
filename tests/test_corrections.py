import unittest
from datetime import date

import pandas as pd

from core.analytics.analyzer import _calculate_volume_ratio
from core.market import corrections, quality
from tests.helpers import make_ohlcv


class CorrectionsTest(unittest.TestCase):
    def test_cancelled_session_removed(self):
        df = make_ohlcv(rows=10, end="2023-02-15")
        self.assertIn(pd.Timestamp("2023-02-08"), df.index)

        cleaned = corrections.drop_cancelled_sessions(df)

        self.assertNotIn(pd.Timestamp("2023-02-08"), cleaned.index)
        self.assertEqual(len(cleaned), 9)

    def test_corporate_action_back_adjusts_prices(self):
        df = make_ohlcv(rows=10, end="2024-09-13", vol=0.0001)
        ex = df.index[5]
        df.loc[ex:, ["open", "high", "low", "close"]] /= 3  # unadjusted 1:3 bonus issue

        action = corrections.CorporateAction("X.IS", ex.date(), 1 / 3)
        fixed = corrections.apply_corporate_actions(df, "X.IS", [action])

        jump = fixed["close"].pct_change().abs().max()
        self.assertLess(jump, 0.01)
        self.assertAlmostEqual(fixed["volume"].iloc[0], df["volume"].iloc[0] * 3)

    def test_other_symbols_untouched(self):
        df = make_ohlcv(rows=5)
        action = corrections.CorporateAction("OTHER.IS", date(2026, 1, 1), 0.5)

        pd.testing.assert_frame_equal(
            corrections.apply_corporate_actions(df, "X.IS", [action]), df
        )

    def test_csv_loading(self):
        import pathlib
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "ca.csv"
            path.write_text(
                "symbol,ex_date,factor,note\nhekts.is,2024-09-09,0.35,test\nbad,row,x,\n",
                "utf-8",
            )
            actions = corrections.load_corporate_actions(path)

        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0].symbol, "HEKTS.IS")


class CalendarQualityTest(unittest.TestCase):
    def test_majority_calendar_ignores_single_gap(self):
        a = make_ohlcv(rows=20, seed=1)
        b = make_ohlcv(rows=20, seed=2)
        c = make_ohlcv(rows=20, seed=3).drop(a.index[10])  # one symbol misses a day

        days = quality.trading_calendar({"A": a, "B": b, "C": c})

        self.assertEqual(len(days), 20)

    def test_market_wide_jump_is_not_flagged(self):
        frames = {}
        for i in range(4):
            df = make_ohlcv(rows=30, seed=i, vol=0.001)
            df.loc[df.index[20]:, ["open", "high", "low", "close"]] *= 1.2
            frames[f"S{i}"] = df

        wide = quality.market_wide_moves(frames)
        q = quality.check_symbol(frames["S0"], "S0", market_wide=wide)

        self.assertIn(frames["S0"].index[20], wide)
        self.assertEqual(q.jumps, [])


class VolumeRatioTest(unittest.TestCase):
    def test_zero_volume_today_is_neutral(self):
        df = make_ohlcv(rows=30)
        df.loc[df.index[-1], "volume"] = 0

        self.assertEqual(_calculate_volume_ratio(df), 1.0)

    def test_zero_days_excluded_from_average(self):
        df = make_ohlcv(rows=30)
        df["volume"] = 100.0
        df.loc[df.index[-5:-1], "volume"] = 0
        df.loc[df.index[-1], "volume"] = 200.0

        self.assertEqual(_calculate_volume_ratio(df), 2.0)


class CorporateActionKindsTest(unittest.TestCase):
    """Bonus and rights issues: the factor is computed from the raw prices."""

    def frame(self, before, after, ex_index=5, rows=10):
        idx = pd.bdate_range("2025-04-01", periods=rows)
        close = [before] * ex_index + [after] * (rows - ex_index)
        return pd.DataFrame(
            {"open": close, "high": close, "low": close, "close": close, "volume": 1000.0},
            index=idx,
            dtype=float,
        )

    def test_rights_issue_formula(self):
        # %100 bedelli at 1 TL on a 2.14 TL stock: TERP = (2.14 + 1) / 2 = 1.57
        df = self.frame(2.14, 1.57)
        ex = df.index[5].date()
        action = corrections.CorporateAction("X.IS", ex, kind="rights", ratio=1.0, price=1.0)
        self.assertAlmostEqual(action.resolve(df), 3.14 / 4.28)
        fixed = corrections.apply_corporate_actions(df, "X.IS", [action])
        self.assertLess(fixed["close"].pct_change().abs().max(), 1e-9)

    def test_bonus_formula(self):
        action = corrections.CorporateAction("X.IS", date(2025, 4, 8), kind="bonus", ratio=10.0)
        self.assertAlmostEqual(action.resolve(self.frame(800, 800 / 11)), 1 / 11)

    def test_factors_use_raw_prices_not_already_adjusted_ones(self):
        # two rights issues; the earlier one must see the raw price before it
        idx = pd.bdate_range("2025-01-01", periods=9)
        close = [10.0] * 3 + [5.5] * 3 + [3.25] * 3  # 100% at 1 TL, then 100% at 1 TL
        df = pd.DataFrame(
            {"open": close, "high": close, "low": close, "close": close, "volume": 1.0}, index=idx
        )
        a1 = corrections.CorporateAction("X.IS", idx[3].date(), kind="rights", ratio=1.0)
        a2 = corrections.CorporateAction("X.IS", idx[6].date(), kind="rights", ratio=1.0)
        fixed = corrections.apply_corporate_actions(df, "X.IS", [a2, a1])
        self.assertLess(fixed["close"].pct_change().abs().max(), 1e-9)

    def test_new_csv_format_and_validation(self):
        import pathlib
        import tempfile

        text = (
            "symbol,ex_date,kind,ratio,price,factor,source,note\n"
            "A.IS,2025-04-14,rights,1,1,,https://example.org,ok\n"
            "B.IS,2024-08-01,bonus,10,,,src,ok\n"
            "C.IS,2022-09-01,factor,,,1.7277,src,ok\n"
            "D.IS,2022-09-01,rights,,1,,src,missing ratio\n"
            "E.IS,2022-09-01,split,2,,,src,unknown kind\n"
            "F.IS,2022-09-01,factor,,,,src,missing factor\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "ca.csv"
            path.write_text(text, "utf-8")
            actions = corrections.load_corporate_actions(path)

        self.assertEqual([a.symbol for a in actions], ["A.IS", "B.IS", "C.IS"])
        self.assertEqual(actions[0].kind, "rights")
        self.assertEqual(actions[0].source, "https://example.org")

    def test_repository_file_is_valid(self):
        import csv

        path = corrections.CORPORATE_ACTIONS_FILE
        with open(path, encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        actions = corrections.load_corporate_actions(path)
        self.assertEqual(len(actions), len(rows), "a row in data/corporate_actions.csv is invalid")
        for row in rows:
            self.assertTrue(row["source"].strip(), f"no source: {row}")


class BadCorporateActionRowTest(unittest.TestCase):
    """A row that cannot be read leaves that stock's history unadjusted: it must be visible, never silent."""

    def test_bad_row_is_reported_and_shown_in_the_daily_report(self):
        import tempfile
        from datetime import date
        from pathlib import Path
        from unittest import mock

        from core.ledger import Entry, append_entry
        from core.market import store
        from core.market.universe import BENCHMARK
        from core.reports.daily import Paths, build_daily
        from tests.helpers import offline_market

        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            bad = d / "corporate_actions.csv"
            bad.write_text(
                "symbol,ex_date,kind,ratio,price,factor,source,note\n"
                "AAA.IS,2026-05-01,factor,,,0.5,test,iyi satır\n"
                "BBB.IS,2026-13-01,factor,,,0.5,test,yanlış tarih\n",
                encoding="utf-8",
            )
            problems: list[str] = []
            actions = corrections.load_corporate_actions(bad, problems=problems)
            self.assertEqual([a.symbol for a in actions], ["AAA.IS"])
            self.assertEqual(len(problems), 1)
            self.assertIn("satır 3", problems[0])
            self.assertIn("BBB.IS", problems[0])

            paths = Paths(d / "ledger.csv", d / "orders.csv", d / "alerts.csv", d / "equity.csv")
            append_entry(Entry(date(2026, 6, 1), "real", "AAA", "buy", 1, 10.0, 0.0), paths.ledger)
            with mock.patch.object(corrections, "CORPORATE_ACTIONS_FILE", bad), offline_market():
                store.update([BENCHMARK, "AAA.IS"])
                text = build_daily(paths, ["AAA.IS"]).text
        self.assertIn("corporate_actions.csv satır 3 okunamadı", text)
