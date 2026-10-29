"""
Talimat E (DECISIONS K-56): the risk budget. The user sets the limits in data/risk_limits.csv; the
system measures and says when a limit is near or passed. No advice: /risk denge is only the
arithmetic of the distance to a limit. Every number here can be checked by hand.
"""

import math
import tempfile
import unittest
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from core.alerts import budget as B


def frame(returns, start=100.0, volume=1e6, first="2025-01-01"):
    close = start * np.cumprod(np.r_[1.0, 1 + np.asarray(returns, dtype=float)])
    index = pd.bdate_range(first, periods=len(close))
    return pd.DataFrame({"open": close, "high": close, "low": close, "close": close, "volume": volume}, index=index)


BASE = np.tile([0.01, -0.01], 150)  # 300 returns


class MeasureTest(unittest.TestCase):
    def setUp(self):
        self.frames = {"A.IS": frame(BASE), "B.IS": frame(2 * BASE)}
        self.bench = frame(BASE)["close"]
        last = {s: df["close"].iloc[-1] for s, df in self.frames.items()}
        self.values = {"A.IS": 50_000.0, "B.IS": 50_000.0}
        self.last = last

    def test_volatility_and_contribution_by_hand(self):
        m = B.measure(self.values, self.frames, 100_000.0, self.bench)
        sigma_a = np.std(BASE[-B.VOL_DAYS:], ddof=1)
        self.assertAlmostEqual(m.volatility, 1.5 * sigma_a * math.sqrt(252), places=6)  # corr 1: 0,5σ + 0,5·2σ
        self.assertAlmostEqual(m.contribution["A.IS"], 1 / 3, places=6)
        self.assertAlmostEqual(m.contribution["B.IS"], 2 / 3, places=6)
        self.assertAlmostEqual(sum(m.contribution.values()), 1.0)
        self.assertAlmostEqual(m.beta, 1.5, places=6)  # 0,5·1 + 0,5·2 against XU100 = A
        self.assertAlmostEqual(m.weights["A.IS"], 0.5)

    def test_liquidity_days_by_hand(self):
        m = B.measure(self.values, self.frames, 100_000.0, self.bench)
        tl = float((self.frames["A.IS"]["close"] * 1e6).shift(1).rolling(20).mean().iloc[-1])
        self.assertAlmostEqual(m.liquidity_days["A.IS"], 50_000.0 / (tl * B.PARTICIPATION))

    def test_drawdown(self):
        perf = pd.Series([1.0, 1.2, 0.9, 1.08])
        self.assertAlmostEqual(B.drawdown(perf), 1 - 1.08 / 1.2)
        self.assertIsNone(B.drawdown(pd.Series(dtype=float)))

    def test_a_position_without_price_is_named(self):
        m = B.measure({"A.IS": 50_000.0, "C.IS": float("nan")}, {**self.frames, "C.IS": pd.DataFrame()},
                      100_000.0, self.bench)
        self.assertIn("C.IS", m.unpriced)
        rows = B.rows(m, {"oynaklik": 0.30})
        self.assertIn("hesaplanamadı", next(r for r in rows if r.name == "oynaklik").text)


class LimitTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "risk_limits.csv"

    def test_file(self):
        self.path.write_text("account,limit,value,note\nhepsi,tek_hisse,20,\nsanal,oynaklik,30,deneme\n"
                             "gercek,var_1g,4,\nhepsi,bilinmeyen,5,\n", encoding="utf-8")
        problems = []
        sanal = B.load_limits("paper", self.path, problems)
        self.assertEqual(sanal, {"tek_hisse": 0.20, "oynaklik": 0.30})
        self.assertEqual(B.load_limits("real", self.path), {"tek_hisse": 0.20, "var_1g": 0.04})
        self.assertEqual(len(problems), 1)
        self.assertEqual(B.load_limits("paper", self.path.with_name("yok.csv")), {})

    def test_states(self):
        self.assertEqual(B.state(0.10, 0.20), "yeşil")
        self.assertEqual(B.state(0.16, 0.20), "sarı")  # 80%
        self.assertEqual(B.state(0.21, 0.20), "kırmızı")
        self.assertEqual(B.state(0.10, None), "sınır tanımlı değil")


class TableTest(unittest.TestCase):
    def setUp(self):
        self.frames = {"A.IS": frame(BASE), "B.IS": frame(2 * BASE)}
        self.bench = frame(BASE)["close"]

    def test_rows_and_text(self):
        m = B.measure({"A.IS": 30_000.0, "B.IS": 10_000.0}, self.frames, 100_000.0, self.bench)
        rows = B.rows(m, {"tek_hisse": 0.25})
        single = next(r for r in rows if r.name == "tek_hisse")
        self.assertAlmostEqual(single.value, 0.30)
        self.assertEqual(single.state, "kırmızı")
        self.assertIn("A", single.text)
        sector = next(r for r in rows if r.name == "tek_sektor")
        self.assertEqual(sector.state, "bilinmiyor")
        text = B.table_text("sanal", m, rows)
        self.assertIn("kullanım %120", text)
        self.assertIn("sınır tanımlı değil", text)
        for word in (" al ", " sat ", "öneri:"):
            self.assertNotIn(word, text.lower().replace("öneri değil", ""))

    def test_what_if_add(self):
        frames = self.frames
        price = float(frames["A.IS"]["close"].iloc[-1])
        values, total = B.what_if({"A.IS": 30_000.0}, 100_000.0, "A.IS", 100, price, paper=True)
        self.assertAlmostEqual(values["A.IS"], 30_000.0 + 100 * price)
        self.assertEqual(total, 100_000.0)  # the paper account pays from cash
        values, total = B.what_if({"A.IS": 30_000.0}, 30_000.0, "B.IS", 10, 50.0, paper=False)
        self.assertEqual((values["B.IS"], total), (500.0, 30_500.0))  # the real account's value is its shares

    def test_rebalance_by_hand(self):
        m = B.measure({"A.IS": 30_000.0, "B.IS": 10_000.0}, self.frames, 100_000.0, self.bench)
        prices = {s: float(df["close"].iloc[-1]) for s, df in self.frames.items()}
        quantities = {s: m.weights[s] * 100_000.0 / prices[s] for s in prices}
        cuts = B.rebalance(m, {"tek_hisse": 0.25}, prices, quantities)
        expected = math.ceil((0.30 - 0.25) * 100_000.0 / prices["A.IS"])
        self.assertEqual(cuts["A.IS"], expected)
        self.assertNotIn("B.IS", cuts)
        text = B.rebalance_text("sanal", cuts, prices)
        self.assertIn("hesap sonucu, öneri değil", text)

    def test_alerts(self):
        m = B.measure({"A.IS": 30_000.0}, self.frames, 100_000.0, self.bench)
        alerts = B.evaluate_limits("paper", B.rows(m, {"tek_hisse": 0.25}), date(2026, 10, 30))
        self.assertEqual([(a.rule, a.severity) for a in alerts], [("risk_siniri:tek_hisse", 3)])
        alerts = B.evaluate_limits("paper", B.rows(m, {"tek_hisse": 0.36}), date(2026, 10, 30))
        self.assertEqual([(a.rule, a.severity) for a in alerts], [("risk_siniri:tek_hisse", 2)])


class DailyLineTest(unittest.TestCase):
    def test_line_and_alerts(self):
        from core.reports import daily

        frames = {"A.IS": frame(BASE)}
        text, alerts = daily._risk_budget("paper", {"A.IS": 30_000.0}, frames, 100_000.0, frame(BASE)["close"],
                                          None, date(2026, 10, 30), limits={"tek_hisse": 0.25})
        self.assertIn("tek hisse kırmızı", text)
        self.assertEqual([a.rule for a in alerts], ["risk_siniri:tek_hisse"])
        text, alerts = daily._risk_budget("paper", {"A.IS": 30_000.0}, frames, 100_000.0, frame(BASE)["close"],
                                          None, date(2026, 10, 30), limits={})
        self.assertIn("sınır tanımlı değil", text)
        self.assertEqual(alerts, [])


class CommandTest(unittest.TestCase):
    def state(self):
        frames = {"A.IS": frame(BASE), "B.IS": frame(2 * BASE)}
        prices = {s: float(df["close"].iloc[-1]) for s, df in frames.items()}
        return B.AccountState("paper", {"A.IS": 30_000.0, "B.IS": 10_000.0}, frames, 100_000.0,
                              frame(BASE)["close"], None, prices, {s: 1000.0 for s in prices})

    def test_parse(self):
        self.assertEqual(B.parse_args([]), ("table", "paper", None))
        self.assertEqual(B.parse_args(["gercek"]), ("table", "real", None))
        self.assertEqual(B.parse_args(["ekle", "thyao", "100"]), ("add", "paper", ("THYAO.IS", 100.0)))
        self.assertEqual(B.parse_args(["denge", "gerçek"]), ("rebalance", "real", None))
        for bad in (["ekle", "THYAO"], ["ekle", "THYAO", "-5"], ["bilinmeyen"]):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                B.parse_args(bad)

    def test_texts(self):
        from unittest import mock

        with mock.patch.object(B, "account_state", return_value=self.state()), \
                mock.patch.object(B, "load_limits", return_value={"tek_hisse": 0.25}):
            table = B.command_text([])
            added = B.command_text(["ekle", "B", "10"])
            denge = B.command_text(["denge"])
        self.assertIn("🛡 Risk bütçesi – sanal", table)
        self.assertIn("Ya şöyle olsaydı", added)
        self.assertIn("emir oluşturulmadı", added)
        self.assertIn("hesap sonucu, öneri değil", denge)
        self.assertIn("A:", denge)

    def test_bot_web_backup_schema(self):
        import asyncio
        from types import SimpleNamespace
        from unittest import mock

        from fastapi.testclient import TestClient

        from bot import commands_risk
        from bot.handlers import COMMANDS, MENU
        from bot.start import HELP_TEXT
        from core import backup
        from core.config.paths import RISK_LIMITS_FILE, ROOT_DIR
        from core.reports import health
        from core.web.app import app
        from tests.test_screen_telegram import fake_update

        self.assertIn("risk", dict(COMMANDS))
        self.assertIn("risk", dict(MENU))
        self.assertIn("/risk", HELP_TEXT)
        self.assertIn(RISK_LIMITS_FILE, backup.PERSONAL_FILES)
        self.assertIn(RISK_LIMITS_FILE, health.SCHEMAS)
        self.assertIn("data/risk_limits.csv", (ROOT_DIR / ".gitignore").read_text(encoding="utf-8"))
        sent = []
        with mock.patch.object(B, "account_state", return_value=self.state()):
            asyncio.run(commands_risk.risk(fake_update(sent), SimpleNamespace(args=[])))
            answer = TestClient(app).get("/risk/sanal").json()
        self.assertIn("Risk bütçesi", sent[0][0])
        self.assertEqual(answer["account"], "sanal")
        self.assertIn("tek_hisse", {r["name"] for r in answer["rows"]})


if __name__ == "__main__":
    unittest.main()
