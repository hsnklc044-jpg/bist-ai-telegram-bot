"""Fundamental fields in /tara (E madde 1, the user's 11.11.2026 decision). Written before the code.

Ten fields from data/fundamentals.csv, each usable from the day after its publication (K-48, K-57): market value,
PD/DD, F/K, return on equity, debt/equity, revenue growth (yearly, quarterly), price/sales (FSO), Piotroski, Altman Z.
KAP tables are cumulative from the start of the year: 12-month figures are this period + last year end − the same
period last year. No data: "veri yok" and the reason; never 0. A change across the TMS 29 switch is not computed."""

import math
import unittest

import pandas as pd

from core.fundamentals import fields as FF

DAYS = pd.bdate_range("2026-03-02", "2026-06-30")


def rows(*items):
    """items: (period_end, published_at, item, value, inflation_adjusted)"""

    out = []
    for period, published, item, value, *flag in items:
        out.append({"symbol": "AAA", "period_end": period, "published_at": published, "item": item,
                    "value": str(value), "unit": "TL", "consolidated": "1",
                    "inflation_adjusted": flag[0] if flag else "1", "source": "test", "recorded_at": "x"})
    return pd.DataFrame(out)


def year(period, published, revenue, net_income, flag="1", **extra):
    base = {"revenue": revenue, "net_income": net_income, "total_equity": 500.0, "paid_in_capital": 100.0,
            "financial_debt": 250.0, "total_assets": 1000.0}
    base.update(extra)
    return [(period, published, k, v, flag) for k, v in base.items()]


DATA = rows(
    *year("2025-03-31", "2025-05-10T18:30:00+03:00", 100.0, 10.0),
    *year("2025-12-31", "2026-03-01T18:30:00+03:00", 500.0, 60.0),
    *year("2026-03-31", "2026-05-11T18:30:00+03:00", 150.0, 20.0),
)
CLOSE = pd.Series(10.0, index=DAYS)


def value(name, day):
    s = FF.series("AAA.IS", name, DAYS, CLOSE, data=DATA)
    return s.loc[pd.Timestamp(day)]


class TimingTest(unittest.TestCase):
    def test_usable_from_the_day_after_publication(self):
        self.assertTrue(math.isnan(value("piyasa_degeri", "2026-03-02")) is False)  # year-end published 01.03 evening
        self.assertEqual(value("fk", "2026-05-11"), value("fk", "2026-05-08"))  # Q1 published 11.05 18:30
        self.assertNotEqual(value("fk", "2026-05-12"), value("fk", "2026-05-11"))


class ValueTest(unittest.TestCase):
    def test_price_fields(self):
        day = "2026-03-10"  # the 2025 year end is known; price 10, 100 shares -> market value 1.000 TL
        self.assertAlmostEqual(value("piyasa_degeri", day), 1000.0 / 1e9)  # milyar TL
        self.assertAlmostEqual(value("pd_dd", day), 1000.0 / 500.0)
        self.assertAlmostEqual(value("fk", day), 1000.0 / 60.0)
        self.assertAlmostEqual(value("fso", day), 1000.0 / 500.0)
        self.assertAlmostEqual(value("ozkaynak_karliligi", day), 60.0 / 500.0 * 100)
        self.assertAlmostEqual(value("borc_ozkaynak", day), 250.0 / 500.0)

    def test_twelve_months_from_cumulative_tables(self):
        day = "2026-05-12"  # Q1 2026 known: TTM net income = 20 + 60 − 10 = 70, revenue = 150 + 500 − 100 = 550
        self.assertAlmostEqual(value("fk", day), 1000.0 / 70.0)
        self.assertAlmostEqual(value("fso", day), 1000.0 / 550.0)
        self.assertAlmostEqual(value("gelir_artisi_yillik", day), (150.0 / 100.0 - 1) * 100)
        self.assertAlmostEqual(value("gelir_artisi_ceyreklik", day), (150.0 / 100.0 - 1) * 100)  # Q1 = year to date

    def test_no_data_is_nan_never_zero(self):
        empty = FF.series("YOK.IS", "fk", DAYS, CLOSE, data=DATA)
        self.assertTrue(empty.isna().all())
        self.assertTrue(math.isnan(value("piotroski", "2026-05-12")))  # its items are not all there

    def test_a_loss_or_negative_equity_has_no_ratio(self):
        data = rows(*year("2025-12-31", "2026-03-01T18:30:00+03:00", 500.0, -5.0, total_equity=-10.0))
        for name in ("fk", "pd_dd", "ozkaynak_karliligi", "borc_ozkaynak"):
            s = FF.series("AAA.IS", name, DAYS, CLOSE, data=data)
            self.assertTrue(math.isnan(s.loc[pd.Timestamp("2026-03-10")]), name)

    def test_a_change_across_the_tms29_switch_is_not_computed(self):
        data = rows(
            *year("2025-03-31", "2025-05-10T18:30:00+03:00", 100.0, 10.0, flag="0"),
            *year("2025-12-31", "2026-03-01T18:30:00+03:00", 500.0, 60.0, flag="1"),
            *year("2026-03-31", "2026-05-11T18:30:00+03:00", 150.0, 20.0, flag="1"),
        )
        s = FF.series("AAA.IS", "gelir_artisi_yillik", DAYS, CLOSE, data=data)
        self.assertTrue(math.isnan(s.loc[pd.Timestamp("2026-05-12")]))
        t = FF.series("AAA.IS", "fk", DAYS, CLOSE, data=data)  # the TTM mixes the two bases too
        self.assertTrue(math.isnan(t.loc[pd.Timestamp("2026-05-12")]))


class ScreenTest(unittest.TestCase):
    def test_the_fields_are_in_the_screen_language(self):
        from core.screen import fields
        from core.screen.language import parse

        for name in FF.NAMES:
            self.assertIn(name, fields.FIELDS)
            self.assertEqual(fields.FIELDS[name].group, "Temel")
        query = parse("pd_dd<1 piotroski>=7 kapanis>sma(200)")
        self.assertIn("pd_dd", query.fields)

    def test_a_stock_without_data_is_named_with_the_reason(self):
        import numpy as np

        from core.screen import engine
        from core.screen.language import parse

        days = pd.bdate_range("2025-01-01", periods=260)
        close = pd.Series(100 * np.exp(0.001 * np.arange(260)), index=days)
        frame = pd.DataFrame({"open": close, "high": close, "low": close, "close": close, "volume": 1e6})
        result = engine.run(parse("pd_dd<1 ele=hayir"), {"AAA.IS": frame}, frame, set(), actions={})
        self.assertEqual(result.matches, [])
        self.assertEqual(result.no_fundamentals, [("AAA.IS", "pd_dd")])
        from core.screen.command import format_result

        self.assertIn("temel veri yok", format_result(result, None).lower())


if __name__ == "__main__":
    unittest.main()
