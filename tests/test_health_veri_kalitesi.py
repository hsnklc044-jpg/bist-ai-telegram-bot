"""#2: the automatic data check among the health checks (last 30 sessions of the stored universe). Synthetic stores,
no network."""

import unittest
from datetime import date, datetime

import pandas as pd

from core.market import quality, store
from core.market.calendar import ISTANBUL
from core.market.corrections import CandleException
from core.reports import health

NOW = datetime(2026, 11, 19, 20, 0, tzinfo=ISTANBUL)  # Thursday, after the 18:30 report
THRESHOLD = "eşik %10 (Pay Piyasası Prosedürü'nden teyit edilmedi)"


def frame(closes, days):
    closes = pd.Series(closes, index=pd.DatetimeIndex([pd.Timestamp(d) for d in days]), dtype=float)
    return pd.DataFrame({"open": closes, "high": closes, "low": closes, "close": closes, "volume": 1000.0})


def universe(**changes):
    days = quality.recent_sessions(date(2026, 11, 19), 45)
    frames = {s: frame([100.0 + i * 0.1 for i in range(len(days))], days) for s in ("AAA.IS", "BBB.IS", "CCC.IS")}
    for symbol, change in changes.items():
        frames[symbol] = change(frames[symbol].copy(), days)
    return frames


def run(frames, exceptions=()):
    return health.data_quality_check(NOW, symbols=list(frames), read=lambda s, start=None: frames[s],
                                     exceptions=list(exceptions))


class DataQualityCheckTest(unittest.TestCase):
    def test_all_fine_is_ok_in_one_line(self):
        check = run(universe())
        self.assertEqual(check.state, health.OK)
        self.assertEqual(check.name, "Veri kalitesi")
        self.assertIn("sorun yok", check.text)
        self.assertNotIn("\n", check.text)

    def test_zero_price_flagged(self):
        def zero(df, days):
            df.loc[pd.Timestamp(days[-3]), ["low", "close"]] = 0.0
            return df

        check = run(universe(**{"BBB.IS": zero}))
        self.assertEqual(check.state, health.WARN)
        self.assertIn("sıfır/negatif fiyat", check.text)
        self.assertIn("BBB", check.text)

    def test_missing_session_flagged(self):
        check = run(universe(**{"AAA.IS": lambda df, days: df.drop(pd.Timestamp(days[-5]))}))
        self.assertEqual(check.state, health.WARN)
        self.assertIn("eksik seans", check.text)
        self.assertIn("AAA", check.text)

    def test_move_beyond_20_percent_flagged_with_unverified_threshold(self):
        # red-team fix: 10.5-20% moves are an INFO count (tests/test_dalga1_redteam.py); beyond 20% warns
        def step(df, days):
            df.loc[df.index >= pd.Timestamp(days[-4]), ["open", "high", "low", "close"]] *= 1.25
            return df

        frames = universe(**{"CCC.IS": step})
        check = run(frames)
        self.assertEqual(check.state, health.WARN)
        self.assertIn("olası düzeltilmemiş sıçrama", check.text)
        self.assertIn("CCC", check.text)
        self.assertIn(THRESHOLD, check.text)
        days = quality.recent_sessions(date(2026, 11, 19), 45)
        explained = CandleException("CCC.IS", days[-4], "real_move", "test")
        self.assertEqual(run(frames, [explained]).state, health.OK)

    def test_old_move_outside_window_ignored(self):
        def step(df, days):
            df.loc[df.index >= pd.Timestamp(days[5]), ["open", "high", "low", "close"]] *= 1.15
            return df

        self.assertEqual(run(universe(**{"CCC.IS": step})).state, health.OK)

    def test_stale_last_bar_flagged(self):
        check = run(universe(**{"AAA.IS": lambda df, days: df[df.index < pd.Timestamp(days[-3])]}))
        self.assertEqual(check.state, health.WARN)
        self.assertIn("bayat", check.text)
        self.assertIn("AAA", check.text)

    def test_no_data_is_unknown(self):
        empty = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        check = health.data_quality_check(NOW, symbols=["AAA.IS"], read=lambda s, start=None: empty, exceptions=[])
        self.assertEqual(check.state, health.UNKNOWN)

    def test_real_store_and_wiring(self):
        frames = universe()
        with store._connect() as conn:
            for symbol, df in frames.items():
                store._write(conn, symbol, df)
        check = health.data_quality_check(NOW, symbols=list(frames), exceptions=[])
        self.assertEqual(check.state, health.OK, check.text)
        self.assertIn("Veri kalitesi", [c.name for c in health.health_checks(NOW, online=False)])


if __name__ == "__main__":
    unittest.main()
