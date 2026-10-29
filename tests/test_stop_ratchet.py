"""
Bağımsız doğrulama M11 (YÜKSEK, docs/validation/M11.md): the trailing stop fell whenever ATR rose,
so the alert opened and closed most days. The stop now only moves up: each day's level (highest
close since entry − 2 × ATR) and the stop is the highest level so far. With too few candles for an
ATR the stop is reported as not computable instead of disappearing silently.
"""

import unittest
from datetime import date

import numpy as np
import pandas as pd

from core.alerts import rules
from core.config import alerts as cfg


def candles(closes, spreads, start="2026-06-01"):
    close = np.asarray(closes, dtype=float)
    spread = np.asarray(spreads, dtype=float)
    index = pd.bdate_range(start, periods=len(close))
    return pd.DataFrame({"open": close, "high": close + spread, "low": close - spread, "close": close,
                         "volume": 1e6}, index=index)


class RatchetTest(unittest.TestCase):
    def test_rising_atr_never_lowers_the_stop(self):
        # 40 calm sessions up to 110, then flat at 108 while the daily range widens
        closes = list(np.linspace(100, 110, 40)) + [108.0] * 20
        spreads = [0.5] * 40 + list(np.linspace(0.5, 3.0, 20))
        df = candles(closes, spreads)
        stops = [rules.stop_level(df.iloc[:n], date(2026, 6, 1)) for n in range(30, len(df) + 1)]
        self.assertTrue(all(b >= a - 1e-12 for a, b in zip(stops, stops[1:], strict=False)))
        # by hand: the best level was reached while ATR was small, before the range widened
        atr = rules._atr(df, cfg.ATR_WINDOW)
        levels = df["close"].cummax() - cfg.STOP_ATR_MULTIPLE * atr
        self.assertAlmostEqual(stops[-1], float(levels.max()))

    def test_alert_stays_open_instead_of_flickering(self):
        closes = list(np.linspace(100, 110, 40)) + [105.0] * 20
        spreads = [0.5] * 40 + list(np.linspace(0.5, 4.0, 20))
        df = candles(closes, spreads)
        fired = [any(a.rule == "stop" for a in rules.evaluate_position("paper", "A.IS", 10, date(2026, 6, 1),
                                                                      df.iloc[:n])) for n in range(41, len(df) + 1)]
        self.assertTrue(all(fired))  # once below the ratcheted stop, every day until the price recovers

    def test_too_few_candles_is_said(self):
        df = candles([100.0] * 8, [0.5] * 8)
        alerts = rules.evaluate_position("paper", "A.IS", 10, date(2026, 6, 1), df)
        self.assertIn("stop_hesaplanamadi", [a.rule for a in alerts])
        self.assertIsNone(rules.stop_level(df, date(2026, 6, 1)))


class UnconfirmedTest(unittest.TestCase):
    """Validation M11 (ORTA): the unconfirmed-action check matched any "teyit", in lower case only."""

    def test_words(self):
        from core.reports.daily import is_unconfirmed

        for note in ("TEYİT BEKLİYOR", "oran teyit edilmedi", "KAP'ta DOĞRULANMADI", "tarih kesinleşmedi",
                     "teyitsiz haber", "doğrulanacak"):
            with self.subTest(note=note):
                self.assertTrue(is_unconfirmed(note))
        for note in ("KAP 1685136, teyit edildi", "ikinci kaynakla doğrulandı", "Yahoo sıçrama günü", ""):
            with self.subTest(note=note):
                self.assertFalse(is_unconfirmed(note))


if __name__ == "__main__":
    unittest.main()
