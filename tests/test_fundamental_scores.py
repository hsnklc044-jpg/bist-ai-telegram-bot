"""
Profesyonel filtreler Aşama 4 (DECISIONS K-57): Piotroski F, Altman Z'', Beneish M, Greenblatt and
Novy-Marx, from the publication-dated store. Every number here is computed by hand; a missing item
is "veri yok", never zero; a value is used only from the day after its publication.
"""

import tempfile
import unittest
from datetime import date
from pathlib import Path

from core.fundamentals import scores as Sc
from core.fundamentals import store

CUR = {"revenue": 1200.0, "cost_of_sales": 800.0, "gross_profit": 400.0, "ebit": 150.0, "net_income": 100.0,
       "operating_cash_flow": 130.0, "depreciation": 40.0, "sga": 120.0, "total_assets": 1000.0,
       "current_assets": 500.0, "receivables": 200.0, "ppe": 300.0, "cash": 50.0, "total_liabilities": 600.0,
       "current_liabilities": 250.0, "long_term_debt": 150.0, "financial_debt": 250.0, "total_equity": 400.0,
       "retained_earnings": 120.0, "paid_in_capital": 100.0}
PREV = {"revenue": 1000.0, "cost_of_sales": 700.0, "gross_profit": 300.0, "ebit": 100.0, "net_income": 60.0,
        "operating_cash_flow": 50.0, "depreciation": 35.0, "sga": 110.0, "total_assets": 900.0,
        "current_assets": 400.0, "receivables": 150.0, "ppe": 280.0, "cash": 40.0, "total_liabilities": 560.0,
        "current_liabilities": 220.0, "long_term_debt": 160.0, "financial_debt": 240.0, "total_equity": 340.0,
        "retained_earnings": 80.0, "paid_in_capital": 100.0}


class PiotroskiTest(unittest.TestCase):
    def test_by_hand(self):
        score, parts = Sc.piotroski(CUR, PREV)
        # ROA 0,1>0 ✓; CFO>0 ✓; ΔROA 0,1−0,0667>0 ✓; CFO>NI ✓; leverage 0,15<0,178 ✓;
        # current ratio 2,0>1,818 ✓; capital unchanged ✓; gross margin 0,333>0,3 ✓; turnover 1,2>1,111 ✓
        self.assertEqual(score, 9)
        self.assertEqual(len(parts), 9)
        worse = dict(CUR, paid_in_capital=120.0, operating_cash_flow=80.0)  # new shares; CFO < NI
        self.assertEqual(Sc.piotroski(worse, PREV)[0], 7)

    def test_partial(self):
        score, parts = Sc.piotroski({k: v for k, v in CUR.items() if k != "long_term_debt"}, PREV)
        self.assertIsNone(score)  # never a full score from 8 parts
        self.assertEqual(sum(v is not None for v in parts.values()), 8)


class AltmanTest(unittest.TestCase):
    def test_by_hand(self):
        x1, x2, x3, x4 = (500 - 250) / 1000, 120 / 1000, 150 / 1000, 400 / 600
        self.assertAlmostEqual(Sc.altman(CUR), 3.25 + 6.56 * x1 + 3.26 * x2 + 6.72 * x3 + 1.05 * x4)
        self.assertEqual(Sc.zone(1.0), "sıkıntı bölgesi")
        self.assertEqual(Sc.zone(2.0), "gri bölge")
        self.assertEqual(Sc.zone(3.0), "güvenli bölge")

    def test_bank_like_balance_sheet(self):
        self.assertEqual(Sc.altman({k: v for k, v in CUR.items() if k != "current_assets"}), Sc.NOT_APPLICABLE)


class BeneishTest(unittest.TestCase):
    def test_by_hand(self):
        dsri = (200 / 1200) / (150 / 1000)
        gmi = (300 / 1000) / (400 / 1200)
        aqi = (1 - (500 + 300) / 1000) / (1 - (400 + 280) / 900)
        sgi = 1200 / 1000
        depi = (35 / (35 + 280)) / (40 / (40 + 300))
        sgai = (120 / 1200) / (110 / 1000)
        lvgi = ((250 + 150) / 1000) / ((220 + 160) / 900)
        tata = (100 - 130) / 1000
        expected = (-4.84 + 0.920 * dsri + 0.528 * gmi + 0.404 * aqi + 0.892 * sgi + 0.115 * depi - 0.172 * sgai
                    + 4.679 * tata - 0.327 * lvgi)
        self.assertAlmostEqual(Sc.beneish(CUR, PREV), expected)
        self.assertIsNone(Sc.beneish(dict(CUR, receivables=None), PREV))


class ValueTest(unittest.TestCase):
    def test_greenblatt_and_novy_marx(self):
        price = 20.0  # market value 20 × 100 shares = 2.000
        ey, roc = Sc.greenblatt(CUR, price)
        self.assertAlmostEqual(ey, 150 / (2000 + 250 - 50))
        self.assertAlmostEqual(roc, 150 / ((500 - 250) + 300))
        gp, bm = Sc.novy_marx(CUR, price)
        self.assertAlmostEqual(gp, 400 / 1000)
        self.assertAlmostEqual(bm, 400 / 2000)


class StoreTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "fundamentals.csv"
        lines = [",".join(store.COLUMNS)]
        for period, published, values, tms in (("2025-09-30", "2025-11-10T18:30:00+03:00", PREV, "1"),
                                               ("2026-09-30", "2026-11-09T18:30:00+03:00", CUR, "1")):
            for item, value in values.items():
                lines.append(f"THYAO,{period},{published},{item},{value},TL,1,{tms},KAP 1,2026-11-10T09:00:00+03:00")
        self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.data = store.load(self.path)

    def test_snapshot_respects_publication(self):
        snap = Sc.snapshot(self.data, "THYAO.IS", date(2026, 11, 10))
        self.assertEqual((snap.period, snap.previous_period), ("2026-09-30", "2025-09-30"))
        self.assertEqual(snap.current["net_income"], 100.0)
        early = Sc.snapshot(self.data, "THYAO.IS", date(2026, 11, 9))  # published at 18:30 that day
        self.assertEqual(early.period, "2025-09-30")
        self.assertIsNone(early.previous_period)

    def test_text(self):
        text = Sc.text("THYAO.IS", self.data, date(2026, 11, 10), price=20.0)
        self.assertIn("Piotroski F: 9/9", text)
        self.assertIn("Altman Z''", text)
        self.assertIn("Beneish M", text)
        self.assertTrue(text.rstrip().endswith(Sc.DISCLAIMER))
        empty = Sc.text("ASELS.IS", self.data, date(2026, 11, 10), price=50.0)
        self.assertIn("veri yok", empty)

    def test_tms29_switch_blocks_changes(self):
        lines = self.path.read_text(encoding="utf-8").splitlines()
        lines = [line.replace(",TL,1,1,", ",TL,1,0,") if ",2025-09-30," in line else line for line in lines]
        self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        snap = Sc.snapshot(store.load(self.path), "THYAO.IS", date(2026, 11, 10))
        self.assertTrue(snap.tms_switch)
        text = Sc.text("THYAO.IS", store.load(self.path), date(2026, 11, 10), price=20.0)
        self.assertIn("TMS 29 geçişi", text)


class CommandTest(unittest.TestCase):
    def test_bot(self):
        import asyncio
        from types import SimpleNamespace
        from unittest import mock

        from bot import analysis
        from bot.handlers import COMMANDS, MENU
        from bot.start import HELP_TEXT
        from tests.test_screen_telegram import fake_update

        self.assertIn("temel", dict(COMMANDS))
        self.assertIn("temel", dict(MENU))
        self.assertIn("/temel", HELP_TEXT)
        sent = []
        with mock.patch("core.reports.daily.raw_bars", return_value=__import__("pandas").DataFrame()):
            asyncio.run(analysis.fundamentals_cmd(fake_update(sent), SimpleNamespace(args=["THYAO"])))
            asyncio.run(analysis.fundamentals_cmd(fake_update(sent), SimpleNamespace(args=[])))
        self.assertIn("veri yok", sent[0][0])
        self.assertIn("Kullanım", sent[1][0])


if __name__ == "__main__":
    unittest.main()
