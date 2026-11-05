"""
Weekly portfolio health report (road plan part 2): distribution, concentration, co-movement,
return after commissions in nominal / real / dollar terms and against BIST 100. What cannot be
measured is said, never estimated.
"""

import unittest
from datetime import date

import numpy as np
import pandas as pd

from core.ledger.book import Entry
from core.reports import portfolio_health as H


def bars_for(prices: dict[str, float], seed=0, n=120, common=None):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(end="2026-10-30", periods=n)
    shared = rng.normal(0, 0.01, n) if common is None else common
    frames = {}
    for i, (s, last) in enumerate(prices.items()):
        r = shared + rng.normal(0, 0.01, n) * (i + 1) * 0.2
        c = np.exp(np.cumsum(r))
        c = c / c[-1] * last
        frames[s] = pd.DataFrame({"open": c, "high": c, "low": c, "close": c, "volume": 1e6}, index=idx)
    return lambda s: frames.get(s, pd.DataFrame())


def buys(*rows):
    return [Entry(date(2026, 9, 1), "real", s, "buy", q, p, 0.0) for s, q, p in rows]


class ConcentrationTest(unittest.TestCase):
    def test_effective_number(self):
        self.assertAlmostEqual(H.concentration({"A": 1, "B": 1, "C": 1, "D": 1}), 4.0)
        self.assertLess(H.concentration({"A": 97, "B": 1, "C": 1, "D": 1}), 1.1)
        self.assertIsNone(H.concentration({}))


class CorrelationTest(unittest.TestCase):
    def test_same_moves_are_near_one_independent_near_zero(self):
        common = np.random.default_rng(1).normal(0, 0.01, 120)
        same = bars_for({"A.IS": 10, "B.IS": 20}, common=common)
        corr, days = H.average_correlation({s: same(s) for s in ("A.IS", "B.IS")})
        self.assertGreater(corr, 0.8)
        self.assertEqual(days, H.CORR_DAYS)
        rng = np.random.default_rng(2)
        idx = pd.bdate_range(end="2026-10-30", periods=120)
        free = {s: pd.DataFrame({"close": np.exp(np.cumsum(rng.normal(0, 0.01, 120)))}, index=idx) for s in "AB"}
        self.assertLess(abs(H.average_correlation(free)[0]), 0.3)

    def test_one_stock_or_few_days(self):
        self.assertEqual(H.average_correlation({"A": pd.DataFrame({"close": [1.0, 2.0]})}), (None, 0))


class BuildTest(unittest.TestCase):
    def setUp(self):
        self.prices = bars_for({"A.IS": 10.0, "B.IS": 20.0})
        self.entries = buys(("A.IS", 300, 10.0), ("B.IS", 50, 20.0))  # values 3000 and 1000

    def test_weights_and_concentration(self):
        h = H.build("real", date(2026, 10, 30), self.entries, None, self.prices, price_bars=self.prices)
        self.assertEqual(list(h.weights), ["A.IS", "B.IS"])
        self.assertAlmostEqual(h.weights["A.IS"], 0.75)
        self.assertAlmostEqual(h.effective, 1 / (0.75 ** 2 + 0.25 ** 2))
        text = H.text(h)
        self.assertIn("en büyük pozisyon A %75", text)
        self.assertIn("ölçülemedi (en az iki günlük değer kaydı", text)
        self.assertIn("öneri değildir", text)

    def test_returns_nominal_real_dollar_and_bench(self):
        equity = pd.Series([4000.0, 4400.0], index=pd.to_datetime(["2026-09-30", "2026-10-30"]))
        bench = pd.Series([100.0, 105.0], index=equity.index)
        cpi = pd.DataFrame()  # no month published: real is "ölçülemedi"
        rates = pd.Series([40.0, 44.0], index=equity.index)
        h = H.build("real", date(2026, 10, 30), self.entries, equity, self.prices, bench, cpi, rates,
                    price_bars=self.prices)
        last4 = h.periods[0]
        self.assertAlmostEqual(last4.nominal, 0.10)
        self.assertAlmostEqual(last4.bench, 0.05)
        self.assertAlmostEqual(last4.usd, 1.10 * 40 / 44 - 1)
        self.assertIsNone(last4.real)
        text = H.text(h)
        self.assertIn("reel ölçülemedi", text)
        self.assertIn("TÜFE ayı yayımlanınca", text)

    def test_money_put_in_is_not_return(self):
        # the second buy (3000 TL) arrives between the records: the value rises 3000, the return is 0
        entries = self.entries + [Entry(date(2026, 10, 15), "real", "A.IS", "buy", 300, 10.0, 0.0)]
        equity = pd.Series([4000.0, 7000.0], index=pd.to_datetime(["2026-09-30", "2026-10-30"]))
        h = H.build("real", date(2026, 10, 30), entries, equity, self.prices, price_bars=self.prices)
        self.assertAlmostEqual(h.periods[0].nominal, 0.0)

    def test_no_positions(self):
        h = H.build("real", date(2026, 10, 30), [], None, self.prices, price_bars=self.prices)
        self.assertIn("Açık pozisyon yok", H.text(h))


class BotTest(unittest.TestCase):
    def test_command_and_weekly_job(self):
        import asyncio
        from types import SimpleNamespace
        from unittest import mock

        from telegram.ext import ApplicationBuilder

        from bot import scheduler

        sent = []

        async def send_message(chat_id, text):
            sent.append(text)

        context = SimpleNamespace(bot=SimpleNamespace(send_message=send_message), job=SimpleNamespace(chat_id=7))
        with mock.patch.object(H, "report", return_value="🩺 rapor"):
            asyncio.run(scheduler.portfolio_health_job(context))
        self.assertEqual(sent, ["🩺 rapor"])
        app = ApplicationBuilder().token("123:abc").build()
        self.assertTrue(scheduler.schedule_portfolio_health(app, 7))
        (job,) = app.job_queue.get_jobs_by_name(scheduler.HEALTH_JOB)
        self.assertEqual(job.chat_id, 7)

    def test_command_is_registered(self):
        from bot import handlers

        self.assertIn("saglik", [name for name, _ in handlers.COMMANDS])


if __name__ == "__main__":
    unittest.main()


class ReportTest(unittest.TestCase):
    def test_report_with_the_live_files(self):
        import tempfile
        from pathlib import Path
        from unittest import mock

        prices = bars_for({"A.IS": 10.0, "B.IS": 20.0, "XU100.IS": 100.0})
        entries = buys(("A.IS", 300, 10.0), ("B.IS", 50, 20.0))
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch("core.ledger.book.load_ledger", return_value=entries), \
                mock.patch("core.reports.daily.adjusted_bars", side_effect=prices), \
                mock.patch("core.reports.daily.raw_bars", side_effect=prices), \
                mock.patch("core.config.paths.EQUITY_LOG_FILE", Path(tmp) / "yok.csv"), \
                mock.patch("core.market.macro.load_cpi", side_effect=OSError("yok")), \
                mock.patch("core.market.macro.load_usdtry", side_effect=OSError("yok")):
            text = H.report(date(2026, 10, 30))
        self.assertIn("Gerçek hesap", text)
        self.assertIn("en büyük pozisyon A %75", text)
        self.assertIn("Sanal hesap", text)
