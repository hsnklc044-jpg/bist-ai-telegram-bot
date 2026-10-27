"""
Every number the daily report shows, checked against a small example that
can be worked out by hand. The arithmetic is written next to each expectation.
"""

import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from core.alerts.portfolio import portfolio_risk
from core.ledger import Entry, append_entry
from core.ledger.paper import place_order
from core.market import store
from core.market.calendar import ISTANBUL
from core.market.universe import BENCHMARK
from core.reports.daily import Paths, build_daily
from tests.helpers import FakeProvider, offline_market

NOW = datetime(2026, 10, 24, 12, 0, tzinfo=ISTANBUL)


def flat(open_, close, rows=300):
    index = pd.bdate_range(end="2026-10-23", periods=rows)
    return pd.DataFrame({"open": open_, "high": max(open_, close), "low": min(open_, close), "close": close,
                         "volume": 2_000_000.0}, index=index)


def frame(returns):
    index = pd.bdate_range(end="2026-10-26", periods=len(returns) + 1)
    close = 100 * np.cumprod(np.r_[1.0, 1 + np.asarray(returns, dtype=float)])
    return pd.DataFrame({"open": close, "high": close, "low": close, "close": close, "volume": 1e6}, index=index)


class RiskByHandTest(unittest.TestCase):
    """
    Two holdings: A 600 TL, B 400 TL. 60 sessions: A falls 5% on 4 of them, otherwise flat; B never moves.
    Account return on a bad day = 0.6 × −5% = −3%, else 0.
    5th percentile of 60 values (linear): position 0.05 × 59 = 2.95, between the 3rd and 4th lowest,
    both −3% → loss estimate 3.0%. On 1.000 TL that is 30 TL.
    Effective positions = 1 / (0.6² + 0.4²) = 1 / 0.52 = 1.92.
    """

    def setUp(self):
        a = [0.0] * 60
        for i in (10, 25, 40, 55):
            a[i] = -0.05
        self.frames = {"A.IS": frame(a), "B.IS": frame([0.0] * 60)}

    def test_without_cash(self):
        risk = portfolio_risk({"A.IS": 600.0, "B.IS": 400.0}, self.frames, total=1000.0)
        self.assertEqual(risk.days, 60)
        self.assertAlmostEqual(risk.var, 0.03, places=12)
        self.assertAlmostEqual(risk.effective_n, 1 / 0.52, places=12)
        self.assertEqual(
            risk.line(),
            "Risk: 1 günlük kayıp, %95 tarihsel: %3,0 (~30 TL; 60 seans); etkin pozisyon sayısı 1,9",
        )

    def test_with_cash_the_loss_is_a_smaller_share_but_the_same_money(self):
        # 1.000 TL cash more: weights 0.3 / 0.2, bad day −1.5% of 2.000 TL = 30 TL; positions still 1.9
        risk = portfolio_risk({"A.IS": 600.0, "B.IS": 400.0}, self.frames, total=2000.0)
        self.assertAlmostEqual(risk.var, 0.015, places=12)
        self.assertAlmostEqual(risk.var * risk.total, 30.0, places=9)
        self.assertAlmostEqual(risk.effective_n, 1 / 0.52, places=12)

    def test_equal_holdings(self):
        # four equal holdings: 1 / (4 × 0.25²) = 4
        frames = {f"S{i}.IS": frame([0.001] * 60) for i in range(4)}
        risk = portfolio_risk({s: 250.0 for s in frames}, frames, total=1000.0)
        self.assertAlmostEqual(risk.effective_n, 4.0, places=12)


class ReportByHandTest(unittest.TestCase):
    """
    Real account: 100 AAA bought at 50 TL + 5 TL fee → cost 5.005 TL, average 50,05.
      Last close 60 → value 6.000 TL; gain 6.000 − 5.005 = 995 TL; 995 / 5.005 = +19,9%.
      Previous recorded value 5.000 TL → daily change 6.000 / 5.000 − 1 = +20,00%.
    Paper account (starts with 100.000 TL): order for 10 BBB fills at the next open 100 TL + 0,05% slippage
      = 100,05; fee 0,1% × 1.000,50 = 1,0005 TL. Cash 100.000 − 1.000,50 − 1,0005 = 98.998,4995.
      Last close 110 → shares 1.100 TL; account 100.098,4995 TL.
      Cost 1.001,5005 → average 100,15; gain 1.100 − 1.001,5005 = 98,4995 TL; 98,4995 / 1.001,5005 = +9,8%.
      Previous recorded value 100.000 → daily change +0,10%.
    Prices never move → 1-day loss estimate 0%; one holding → 1,0 effective positions.
    """

    def test_numbers(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            paths = Paths(d / "ledger.csv", d / "orders.csv", d / "alerts.csv", d / "equity.csv")
            paths.equity.write_text(
                "date,account,value,cash,invested,positions\n"
                "2026-10-22,real,5000.00,0.00,5000.00,1\n"
                "2026-10-22,paper,100000.00,100000.00,0.00,0\n",
                encoding="utf-8",
            )
            append_entry(Entry(date(2026, 6, 1), "real", "AAA", "buy", 100, 50.0, 5.0), paths.ledger)
            place_order("BBB", "buy", 10, now=datetime(2026, 10, 20, 12, tzinfo=ISTANBUL),
                        orders_path=paths.orders, ledger_path=paths.ledger)
            provider = FakeProvider()
            provider.overrides.update({"AAA.IS": flat(60.0, 60.0), "BBB.IS": flat(100.0, 110.0),
                                       BENCHMARK: flat(10_000.0, 10_000.0)})
            with offline_market(provider):
                store.update([BENCHMARK, "AAA.IS", "BBB.IS"], now=NOW)
                text = build_daily(paths, ["AAA.IS", "BBB.IS"]).text

        self.assertIn("Hisse değeri 6.000 TL", text)
        self.assertIn("AAA: 100 adet × 60,00 = 6.000 TL (maliyet 50,05; +995 TL / +%19,9)", text)
        self.assertIn("Günlük değişim +%20,00", text)
        self.assertIn("Değer 100.098 TL (nakit 98.998 TL, hisse 1.100 TL)", text)
        self.assertIn("BBB: 10 adet × 110,00 = 1.100 TL (maliyet 100,15; +98 TL / +%9,8)", text)
        self.assertIn("Günlük değişim +%0,10", text)
        self.assertIn("100,05 TL'den", text)
        self.assertIn("komisyon 1,00 TL", text)
        risk_lines = [line for line in text.splitlines() if line.startswith("Risk:")]
        self.assertEqual(len(risk_lines), 2)
        for line in risk_lines:
            self.assertIn("%0,0 (~0 TL;", line)
            self.assertIn("etkin pozisyon sayısı 1,0", line)


if __name__ == "__main__":
    unittest.main()


class RealAccountFlowsTest(unittest.TestCase):
    """
    The real account's value is the market value of its shares, so buying shares raises it and
    selling lowers it without any gain or loss. Daily change and drawdown must leave those out:
    return = (value today − money put in since the last record) / value at the last record − 1.
    """

    def run_report(self, d, entries, previous_value):
        paths = Paths(d / "ledger.csv", d / "orders.csv", d / "alerts.csv", d / "equity.csv")
        paths.equity.write_text(
            "date,account,value,cash,invested,positions\n"
            f"2026-10-22,real,{previous_value:.2f},0.00,{previous_value:.2f},1\n",
            encoding="utf-8",
        )
        for e in entries:
            append_entry(e, paths.ledger, today=date(2026, 10, 24))
        provider = FakeProvider()
        provider.overrides.update({"AAA.IS": flat(50.0, 50.0), BENCHMARK: flat(10_000.0, 10_000.0)})
        with offline_market(provider):
            store.update([BENCHMARK, "AAA.IS"], now=NOW)
            result = build_daily(paths, ["AAA.IS"])
        real = result.text.split("💼 Gerçek hesap")[1].split("💼")[0]
        return real, result

    def test_buying_more_is_not_a_gain(self):
        # 22.10: 100 AAA = 5.000 TL. 23.10: 100 more bought at 50 (+5 TL fee); price still 50.
        # value 10.000; money in 5.005 → (10.000 − 5.005) / 5.000 − 1 = −0,10% (the fee), not +100%
        with tempfile.TemporaryDirectory() as tmp:
            real, _ = self.run_report(Path(tmp), [
                Entry(date(2026, 6, 1), "real", "AAA", "buy", 100, 50.0, 0.0),
                Entry(date(2026, 10, 23), "real", "AAA", "buy", 100, 50.0, 5.0),
            ], previous_value=5000.0)
        self.assertIn("Günlük değişim -%0,10", real)

    def test_selling_half_is_not_a_drawdown(self):
        # 22.10: 200 AAA = 10.000 TL. 23.10: 100 sold at 50 (5 TL fee) → value 5.000, money out 4.995
        # → (5.000 + 4.995) / 10.000 − 1 = −0,05%; no "hesap zirvesinden %50 aşağıda" alert
        with tempfile.TemporaryDirectory() as tmp:
            real, result = self.run_report(Path(tmp), [
                Entry(date(2026, 6, 1), "real", "AAA", "buy", 200, 50.0, 0.0),
                Entry(date(2026, 10, 23), "real", "AAA", "sell", 100, 50.0, 5.0),
            ], previous_value=10000.0)
        self.assertIn("Günlük değişim -%0,05", real)
        self.assertNotIn("hesap_dusus", [a.rule for _, a in result.events if hasattr(a, "rule")])
        self.assertNotIn("zirvesinden", result.text)


class HeldOutsideUniverseTest(unittest.TestCase):
    """A stock held (or ordered) that is not in the BIST 100 list must still be priced with fresh data."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        d = Path(tmp.name)
        self.paths = Paths(d / "ledger.csv", d / "orders.csv", d / "alerts.csv", d / "equity.csv")
        append_entry(Entry(date(2026, 6, 1), "real", "XYZ", "buy", 10, 20.0, 0.0), self.paths.ledger)
        place_order("QQQ", "buy", 5, now=datetime(2026, 10, 20, 12, tzinfo=ISTANBUL),
                    orders_path=self.paths.orders, ledger_path=self.paths.ledger)

    def test_daily_update_covers_held_and_ordered_symbols(self):
        from core.reports import daily

        symbols = daily.symbols_to_update(self.paths, ["AAA.IS"])
        self.assertEqual(symbols[:2], [BENCHMARK, "AAA.IS"])
        self.assertIn("XYZ.IS", symbols)
        self.assertIn("QQQ.IS", symbols)

    def test_run_prices_a_held_stock_at_its_latest_close(self):
        from types import SimpleNamespace
        from unittest import mock

        from core.reports import daily

        provider = FakeProvider()
        old = flat(20.0, 20.0)
        provider.overrides.update({"AAA.IS": flat(10.0, 10.0), BENCHMARK: flat(10_000.0, 10_000.0),
                                   "XYZ.IS": old.iloc[:-10], "QQQ.IS": flat(30.0, 30.0)})
        with offline_market(provider):
            store.update(["XYZ.IS"], now=NOW.replace(tzinfo=None))  # naive, as in production; stored days ago (before the 15-minute refresh window), 10 sessions behind
            fresh = old.copy()
            fresh.iloc[-1, fresh.columns.get_loc("close")] = 25.0
            provider.overrides["XYZ.IS"] = fresh
            # only the price update and the report itself: no backup, score log or health lines
            with mock.patch.object(daily, "Paths", lambda: self.paths), \
                    mock.patch.object(daily, "load_universe", return_value=["AAA.IS"]), \
                    mock.patch.object(daily, "_record_scores"), \
                    mock.patch.object(daily, "_with_backup_line", side_effect=lambda t: t), \
                    mock.patch.object(daily, "_with_health_warnings", side_effect=lambda t: t):
                result = daily._run_locked(SimpleNamespace(no_update=False, send=False, force=False))
        self.assertIn("XYZ: 10 adet × 25,00 = 250 TL", result.text)
        self.assertNotIn("Güncel olmayan", result.text)

    def test_stale_held_stock_is_named(self):
        provider = FakeProvider()
        provider.overrides.update({"AAA.IS": flat(10.0, 10.0), BENCHMARK: flat(10_000.0, 10_000.0),
                                   "XYZ.IS": flat(20.0, 20.0).iloc[:-10]})
        with offline_market(provider):
            store.update([BENCHMARK, "AAA.IS", "XYZ.IS"], now=NOW)
            text = build_daily(self.paths, ["AAA.IS"]).text
        self.assertIn("Güncel olmayan: XYZ", text)


class PortfolioCommandTest(unittest.TestCase):
    """/portfolio and the daily report value holdings with one function; an old price says its date."""

    def test_old_price_shows_its_date_and_values_match_the_report(self):
        from core.ledger.service import portfolio_text

        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            paths = Paths(d / "ledger.csv", d / "orders.csv", d / "alerts.csv", d / "equity.csv")
            append_entry(Entry(date(2026, 6, 1), "real", "XYZ", "buy", 10, 20.0, 0.0), paths.ledger)
            append_entry(Entry(date(2026, 6, 1), "real", "AAA", "buy", 4, 10.0, 0.0), paths.ledger)
            provider = FakeProvider()
            provider.overrides.update({"AAA.IS": flat(10.0, 12.0), BENCHMARK: flat(10_000.0, 10_000.0),
                                       "XYZ.IS": flat(20.0, 21.0).iloc[:-10]})
            with offline_market(provider):
                store.update([BENCHMARK, "AAA.IS", "XYZ.IS"], now=NOW)
                text = portfolio_text(paths.ledger)
                report = build_daily(paths, ["AAA.IS"]).text
        old_day = flat(1.0, 1.0).index[-11]
        self.assertIn(f"son 21,00 ({old_day:%d.%m} tarihli)", text)  # XYZ: 10 sessions behind XU100
        self.assertIn("son 12,00 →", text)  # AAA: current, no date
        self.assertIn("Hisse değeri 258 TL", report)  # 10 × 21 + 4 × 12, same prices in both
        self.assertIn("XYZ: 10 adet × 21,00", report)


class ManualReportAlertsTest(unittest.TestCase):
    """/report shows the same alerts as the 18:30 report but must not use up their "🆕" there."""

    def test_new_alert_is_still_new_in_the_scheduled_report(self):
        from unittest import mock

        from bot import portfolio
        from core.reports import daily

        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            paths = Paths(d / "ledger.csv", d / "orders.csv", d / "alerts.csv", d / "equity.csv")
            append_entry(Entry(date(2026, 6, 1), "real", "AAA", "buy", 10, 10.0, 0.0), paths.ledger)
            provider = FakeProvider()
            provider.overrides.update({"AAA.IS": flat(10.0, 10.0), BENCHMARK: flat(10_000.0, 10_000.0)})
            with offline_market(provider), \
                    mock.patch.object(daily, "Paths", lambda: paths), \
                    mock.patch.object(daily, "load_universe", return_value=["AAA.IS"]):
                manual = portfolio._daily_text()
                scheduled = build_daily(paths, ["AAA.IS"]).text
        self.assertIn("🆕 [orta] AAA: bu hissenin hesaptaki payı %100", manual)
        self.assertIn("🆕 [orta] AAA: bu hissenin hesaptaki payı %100", scheduled)


class ChangeLabelTest(unittest.TestCase):
    """After days without a record (PC off) the change covers them all and must say since when."""

    def run_report(self, previous_day):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            paths = Paths(d / "ledger.csv", d / "orders.csv", d / "alerts.csv", d / "equity.csv")
            paths.equity.write_text("date,account,value,cash,invested,positions\n"
                                    f"{previous_day},paper,99000.00,99000.00,0.00,0\n", encoding="utf-8")
            provider = FakeProvider()
            provider.overrides.update({BENCHMARK: flat(10_000.0, 10_000.0)})
            with offline_market(provider):
                store.update([BENCHMARK], now=NOW)
                return build_daily(paths, [BENCHMARK]).text

    def test_previous_session_is_a_daily_change(self):
        self.assertIn("Günlük değişim +%1,01", self.run_report("2026-10-22"))  # Thu → Fri 23.10

    def test_older_record_names_its_date(self):
        text = self.run_report("2026-10-19")  # Mon → Fri: four sessions
        self.assertNotIn("Günlük değişim", text)
        self.assertIn("19.10 kaydından bu yana değişim +%1,01 (4 seans)", text)
