"""
Stress test, currency shock (road plan part 2): the worst TL falls against the dollar in the stored
CBRT rates, found from the data; each holding with its own TL return over the same days, and the
position's change in dollars.
"""

import unittest

import pandas as pd

from core.reports import stress
from tests.test_stress import XU, closes


def rates(values, start="2024-01-01"):
    return pd.Series(values, index=pd.bdate_range(start=start, periods=len(values)), dtype=float)


# USD/TRY: flat 30, then +10% in one day (TL loses ~9,1%), then flat
USD = rates([30.0] * 30 + [33.0] + [33.0] * 32)


class FxWindowTest(unittest.TestCase):
    def test_the_worst_tl_fall_is_found(self):
        (one, *_) = stress.fx_windows(USD)
        self.assertEqual(one.sessions, 1)
        self.assertAlmostEqual(one.market, 30 / 33 - 1)  # TL's value in dollars

    def test_holding_in_tl_and_in_dollars(self):
        (one, *_) = stress.fx_windows(USD)
        frames = {"AAA.IS": closes([50] * 30 + [55] + [55] * 32)}  # +10% in TL the same day
        s = stress.fx_scenario(one, {"AAA.IS": 1000.0}, frames, XU)
        (row,) = s.rows
        self.assertAlmostEqual(row.change, 0.10)
        self.assertAlmostEqual(stress.in_dollars(row.change, one), 1.10 * 30 / 33 - 1)

    def test_text_section(self):
        (one, *_) = stress.fx_windows(USD)
        s = stress.fx_scenario(one, {"AAA.IS": 1000.0}, {"AAA.IS": closes([50] * 63)}, XU)
        text = "\n".join(stress.fx_lines([s], total=1000.0))
        self.assertIn("Kur şoku", text)
        self.assertIn("dolar/TL +%10,0", text)
        self.assertIn("dolar bazında -%9,1", text)

    def test_no_rates(self):
        self.assertIn("kur verisi yok", "\n".join(stress.fx_lines([], total=1000.0, have_rates=False)))


if __name__ == "__main__":
    unittest.main()
