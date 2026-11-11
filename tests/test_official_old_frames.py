"""r2 frames from the old-system files (K-92). Written before the code and before any measurement.

BAZ FIYAT of a day is the previous day's AOF; a deviation of more than 0.5 % is the exchange's corporate action factor
(split, rights, dividend) and the series before it is scaled by it. The 2005 currency change is no action."""

import unittest
from datetime import date

import pytest

from core.official import frames_old as OF
from core.official.prices import Row


def row(day, close, base, aof, bist100=1, code="AAA"):
    return Row(code=code, day=day, open=None, high=close, low=close, close=close, prev_close=None, value=close * 10,
               quantity=10.0, bist100=bist100, bist30=None, base=base, aof=aof)


class FactorTest(unittest.TestCase):
    def test_a_split_day_is_scaled_by_the_exchange_factor(self):
        rows = [row(date(2006, 3, 8), 13.60, 13.50, 13.57), row(date(2006, 3, 9), 13.70, 13.57, 13.65),
                row(date(2006, 3, 10), 7.00, 6.95, 7.00)]  # AKGRT 10.03.2006: 6,95 / 13,57 = 0,512
        frame = OF.frame(rows)
        r = frame["close"].pct_change()
        self.assertAlmostEqual(r.iloc[2], 7.00 / (13.70 * (6.95 / 13.65)) - 1)
        self.assertAlmostEqual(frame["close"].iloc[-1], 7.00)  # the latest price is the traded one

    def test_a_dividend_is_adjusted_too_and_noise_is_not(self):
        rows = [row(date(2006, 3, 28), 11.20, 11.10, 11.18), row(date(2006, 3, 29), 10.95, 10.90, 10.96)]
        r = OF.frame(rows)["close"].pct_change()
        self.assertAlmostEqual(r.iloc[1], 10.95 / (11.20 * (10.90 / 11.18)) - 1)  # 0,975: a dividend
        quiet = [row(date(2006, 4, 3), 10.00, 9.98, 10.02), row(date(2006, 4, 4), 10.10, 10.01, 10.05)]
        r = OF.frame(quiet)["close"].pct_change()
        self.assertAlmostEqual(r.iloc[1], 10.10 / 10.00 - 1)  # within 0,5 %: no action

    def test_the_lira_value_stays_as_traded(self):
        rows = [row(date(2006, 3, 9), 13.70, 13.57, 13.65), row(date(2006, 3, 10), 7.00, 6.95, 7.00)]
        frame = OF.frame(rows)
        self.assertAlmostEqual((frame["close"] * frame["volume"]).iloc[0], 13.70 * 10)

    def test_the_period_is_the_old_system_and_never_the_holdout(self):
        with pytest.raises(ValueError):
            OF.load(date(2002, 1, 2), date(2016, 1, 4))  # the old system ends on 13.11.2015
        self.assertEqual(OF.OLD_SYSTEM_UNTIL, date(2015, 11, 13))


if __name__ == "__main__":
    unittest.main()
