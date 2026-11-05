"""
Faz C, M32-3 (the paper book): the hourly follow applies the daily rule. A day's own high lifts
the trailing stop only from the next session on, as on daily candles; it used to lift it within
the same day, so the hourly path stopped more often and earlier than the measured rule.
"""

import unittest
from datetime import date

import pandas as pd

from core.signals import store as S
from tests.test_m32_revalidation import hourly_day, signal

TZ = "Europe/Istanbul"


def to_daily(hourly: pd.DataFrame) -> pd.DataFrame:
    day = hourly.index.tz_convert(TZ).tz_localize(None).normalize()
    g = hourly.groupby(day)
    return pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(),
                         "close": g["close"].last()})


class SameRuleTest(unittest.TestCase):
    def frame(self):
        day2 = pd.concat([hourly_day("2026-10-02", 100, 100.5, 99.9, 100, hours=1).set_axis(
                              pd.DatetimeIndex([pd.Timestamp("2026-10-02 10:00", tz=TZ)])),
                          hourly_day("2026-10-02", 102, 103.5, 102, 103, hours=1).set_axis(
                              pd.DatetimeIndex([pd.Timestamp("2026-10-02 11:00", tz=TZ)])),
                          hourly_day("2026-10-02", 102, 102.5, 101, 101.5, hours=1).set_axis(
                              pd.DatetimeIndex([pd.Timestamp("2026-10-02 12:00", tz=TZ)]))])
        return pd.concat([hourly_day("2026-10-01", 100, 100.5, 99.8, 100), day2,
                          hourly_day("2026-10-05", 102, 102.5, 101, 101.5)])

    def test_same_day_high_does_not_lift_the_stop_that_day(self):
        got = S._follow(signal(created=date(2026, 10, 1)), self.frame(), expire=False)
        self.assertEqual(got["status"], "stop")
        self.assertEqual(got["exit_date"], "2026-10-05")  # not 02.10 at 101,43
        self.assertAlmostEqual(got["exit_price"], 103.5 * (1 - S.STOP))

    def test_hourly_and_daily_agree(self):
        hourly = self.frame()
        a = S._follow(signal(created=date(2026, 10, 1)), hourly, expire=False)
        b = S._follow(signal(created=date(2026, 10, 1)), to_daily(hourly), expire=False)
        for key in ("status", "exit_date", "exit_price", "entry_price"):
            self.assertEqual(a.get(key), b.get(key), key)


if __name__ == "__main__":
    unittest.main()
