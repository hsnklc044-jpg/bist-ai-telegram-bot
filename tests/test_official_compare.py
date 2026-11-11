"""Using the official end-of-day data (K madde 2–3, the user's 11.11.2026 decision). Written before the code.

Closed months: the official closes are level 1 and Yahoo is checked against them on daily returns with the unchanged
crosscheck rules; the summary feeds the "Veri doğruluğu" objective with the source "Borsa İstanbul resmî gün sonu".
The current month stays on Yahoo (level 3) until its file arrives. Corporate action days come from the exchange's own
code; membership is compared with our list after ticker renames, and a day a share did not trade is not "not a
member". On the first trading day of a month, until last month's price and index files are in the inbox, the daily
report says so in one line."""

import json
import unittest
from datetime import date, datetime

import pandas as pd
import pytest

from core.market import second_source, trust
from core.market.calendar import ISTANBUL
from core.official import compare, prices

NOW = datetime(2026, 11, 11, 3, 0, tzinfo=ISTANBUL)
OCT = pd.bdate_range("2026-10-01", "2026-10-30")


@pytest.fixture(autouse=True)
def _db(tmp_path, monkeypatch):
    monkeypatch.setattr(prices, "OFFICIAL_DB", tmp_path / "official.db")
    monkeypatch.setattr(second_source, "SUMMARY_FILE", tmp_path / "price_second_source.json")
    monkeypatch.setattr(trust, "SECOND_SOURCE_FILE", tmp_path / "price_second_source.json")
    monkeypatch.setattr(compare, "REPORT_DIR", tmp_path)
    trust.clear_cache()


def put(rows):
    """rows: (code, day, close, bist100, corp_action)"""
    with prices._connect() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO official_prices (code, date, open, high, low, close, prev_close, value, quantity, "
            "bist100, bist30, corp_action, file) VALUES (?, ?, NULL, ?, ?, ?, NULL, 1, 1, ?, 0, ?, 'f')",
            [(c, d.isoformat() if isinstance(d, date) else d, cl, cl, cl, m, a) for c, d, cl, m, a in rows])


def series(start=100.0, step=0.004):
    return [start * (1 + step) ** i for i in range(len(OCT))]


def bars_from(closes: dict):
    def bars(symbol):
        values = closes.get(symbol.removesuffix(".IS"))
        if values is None:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        return pd.DataFrame({"open": values, "high": values, "low": values, "close": values, "volume": 1.0},
                            index=OCT[: len(values)])
    return bars


class YahooCheckTest(unittest.TestCase):
    def test_a_clean_month_feeds_the_accuracy_objective_with_the_official_source(self):
        official = series()
        put([(c, d.date(), v, 1, None) for c in ("AAA", "BBB") for d, v in zip(OCT, official)])
        yahoo = {"AAA": [v * 0.97 for v in official], "BBB": official}  # a constant (dividend) factor is fine
        summary = compare.yahoo_check(NOW, bars=bars_from(yahoo), codes=["AAA", "BBB"])
        self.assertEqual(summary["checked"], 2)
        self.assertEqual(summary["differing"], [])
        self.assertEqual(summary["source"], compare.SOURCE)
        self.assertEqual(summary["period"], "2026-10")
        saved = json.loads(second_source.SUMMARY_FILE.read_text(encoding="utf-8"))
        self.assertEqual(saved["source"], "Borsa İstanbul resmî gün sonu")

    def test_a_wrong_close_is_named_and_a_corporate_action_day_is_not(self):
        official = series()
        wrong = list(official)
        wrong[10:] = [v * 1.05 for v in wrong[10:]]  # an unexplained 5 % step in Yahoo (a one-day error that is
        # undone the next session is reported apart as a wrong close, by the unchanged crosscheck rules)
        split = list(official)
        split[12:] = [v / 2 for v in split[12:]]  # official raw prices halve on the split day
        put([("AAA", d.date(), v, 1, None) for d, v in zip(OCT, official)])
        put([("BBB", d.date(), v, 1, "03" if i == 12 else None) for i, (d, v) in enumerate(zip(OCT, split))])
        summary = compare.yahoo_check(NOW, bars=bars_from({"AAA": wrong, "BBB": official}), codes=["AAA", "BBB"])
        self.assertEqual(summary["differing"], ["AAA"])
        report = (compare.REPORT_DIR / "resmi_karsilastirma_2026-10.txt").read_text(encoding="utf-8")
        self.assertIn("AAA", report)

    def test_no_official_month_no_check(self):
        self.assertIsNone(compare.yahoo_check(NOW, bars=bars_from({}), codes=["AAA"]))
        self.assertFalse(second_source.SUMMARY_FILE.exists())


class LevelTest(unittest.TestCase):
    def test_a_closed_month_with_its_file_is_level_1_and_the_current_month_level_3(self):
        put([("AAA", "2026-10-30", 10.0, 1, None)])
        self.assertEqual(trust.for_day(date(2026, 10, 30), NOW).level, 1)
        self.assertIn("Borsa İstanbul", trust.for_day(date(2026, 10, 30), NOW).source)
        self.assertEqual(trust.for_day(date(2026, 11, 10), NOW).level, 3)

    def test_the_monthly_official_check_does_not_lift_the_current_month(self):
        official = series()
        put([("AAA", d.date(), v, 1, None) for d, v in zip(OCT, official)])
        compare.yahoo_check(NOW, bars=bars_from({"AAA": official}), codes=["AAA"])
        trust.clear_cache()
        self.assertEqual(trust.price_trust(NOW).level, 3)


class CorporateActionTest(unittest.TestCase):
    def test_official_codes_against_our_file(self):
        from core.market.corrections import CorporateAction

        put([("TUKAS", "2025-02-04", 2.04, 0, "03"), ("ZZZZ", "2025-03-03", 5.0, 0, "01"),
             ("GSRAY", "2025-07-07", 6.0, 0, "01")])
        ours = [CorporateAction("TUKAS.IS", date(2025, 2, 3), kind="bonus", ratio=2.05),
                CorporateAction("GSRAY.IS", date(2025, 7, 7), kind="rights", ratio=1.5),
                CorporateAction("AKBNK.IS", date(2025, 4, 1), factor=0.5)]
        got = compare.corporate_actions_report(ours, codes={"TUKAS", "ZZZZ", "GSRAY", "AKBNK"})
        self.assertEqual(got.matched, [("GSRAY", date(2025, 7, 7))])
        self.assertEqual(got.shifted, [("TUKAS", date(2025, 2, 3), date(2025, 2, 4), "03")])
        self.assertEqual(got.only_official, [("ZZZZ", date(2025, 3, 3), "01")])
        self.assertEqual(got.only_ours, [("AKBNK", date(2025, 4, 1))])


class MembershipTest(unittest.TestCase):
    def test_renames_are_followed_and_a_day_without_trade_is_not_a_difference(self):
        put([("KOZAL", "2025-01-02", 1.0, 1, None), ("THYAO", "2025-01-02", 1.0, 1, None),
             ("THYAO", "2025-01-03", 1.0, 1, None), ("NEWCO", "2025-01-03", 1.0, 1, None)])
        ours = {date(2025, 1, 2): {"TRALT", "THYAO"}, date(2025, 1, 3): {"TRALT", "THYAO"}}
        got = compare.membership_report([date(2025, 1, 2), date(2025, 1, 3)], lambda d: ours[d])
        # 03.01: TRALT has no row (no trade) -> not a difference; NEWCO flagged only in the official file
        self.assertEqual(got.days, 2)
        self.assertEqual(got.differences, [(date(2025, 1, 3), ["NEWCO"], [])])


class ReminderTest(unittest.TestCase):
    def test_from_the_first_trading_day_until_both_files_are_in(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as d:
            price_dir, index_dir = Path(d, "bist"), Path(d, "bist_endeks")
            price_dir.mkdir()
            index_dir.mkdir()
            first = date(2026, 11, 2)  # Monday, the first trading day of November 2026
            self.assertIsNone(compare.reminder(date(2026, 11, 1), price_dir, index_dir))  # before the first trading day
            line = compare.reminder(first, price_dir, index_dir)
            self.assertEqual(line, "Senden beklenen: geçen ayın borsa fiyat ve endeks dosyalarını indir")
            (price_dir / "PP_GUNSONUFIYATHACIM.M.202610.csv").write_text("x", encoding="utf-8")
            self.assertIsNotNone(compare.reminder(date(2026, 11, 5), price_dir, index_dir))  # index still missing
            (index_dir / "202610").mkdir()
            (index_dir / "202610" / "PP_GUNSONUENDEKS_M.csv").write_text("x", encoding="utf-8")
            self.assertIsNone(compare.reminder(date(2026, 11, 5), price_dir, index_dir))

    def test_nothing_when_the_official_data_is_not_used_here(self):
        from pathlib import Path

        self.assertIsNone(compare.reminder(date(2026, 11, 2), Path("yok/bist"), Path("yok/bist_endeks")))

    def test_the_daily_report_carries_it(self):
        import inspect

        from core.reports import daily

        self.assertIn("compare.reminder(", inspect.getsource(daily))


class JobTest(unittest.TestCase):
    def test_the_night_job_checks_yahoo_after_the_import(self):
        import inspect

        from bot import scheduler

        source = inspect.getsource(scheduler.official_prices_job)
        self.assertIn("compare.yahoo_check", source)
        self.assertLess(source.index("import_folder"), source.index("compare.yahoo_check"))


if __name__ == "__main__":
    unittest.main()
