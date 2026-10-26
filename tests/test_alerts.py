import tempfile
import unittest
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from core.alerts import evaluate_account, evaluate_position, open_alerts, update_alert_log
from core.config import alerts as cfg

D = date.fromisoformat


def candles(closes, start="2026-01-02", spread=0.01, volume=1_000_000.0):
    idx = pd.bdate_range(start, periods=len(closes))
    c = pd.Series(closes, index=idx, dtype=float)
    return pd.DataFrame(
        {"open": c, "high": c * (1 + spread), "low": c * (1 - spread), "close": c, "volume": volume}
    )


def rules(alerts):
    return {a.rule for a in alerts}


class StopTest(unittest.TestCase):
    def test_stop_broken_after_drop_from_high(self):
        closes = [100.0] * 30 + [120.0] * 10 + [100.0]
        df = candles(closes)
        out = evaluate_position("paper", "X.IS", 10, df.index[0].date(), df)
        self.assertIn("stop", rules(out))
        stop = next(a for a in out if a.rule == "stop")
        self.assertEqual(stop.severity, 3)
        self.assertLess(stop.value, stop.threshold)

    def test_quiet_position_has_no_stop_alert(self):
        df = candles([100.0 + 0.1 * i for i in range(60)])
        out = evaluate_position("paper", "X.IS", 10, df.index[0].date(), df)
        self.assertFalse({"stop", "stop_yakin"} & rules(out))

    def test_high_only_counts_since_entry(self):
        closes = [200.0] * 30 + [100.0] * 30  # the old high is before the purchase
        df = candles(closes)
        out = evaluate_position("paper", "X.IS", 10, df.index[30].date(), df)
        self.assertNotIn("stop", rules(out))


class OtherRulesTest(unittest.TestCase):
    def test_locked_limit_down_streak(self):
        closes = [100.0] * 30 + [90.0, 81.0]
        df = candles(closes)
        for i in (30, 31):
            df.iloc[i, :4] = df["close"].iloc[i]
        out = evaluate_position("real", "X.IS", 1, df.index[0].date(), df)
        lock = next(a for a in out if a.rule == "taban_kilit")
        self.assertEqual(lock.value, 2)

    def test_parabolic(self):
        closes = list(np.linspace(10, 10, 110)) + list(np.linspace(10, 25, 30))
        out = evaluate_position("paper", "X.IS", 1, D("2026-01-02"), candles(closes))
        self.assertIn("parabolik", rules(out))

    def test_liquidity_and_concentration(self):
        df = candles([10.0] * 40, volume=1000.0)  # turnover 10_000 TL per day
        out = evaluate_position("paper", "X.IS", 100, df.index[0].date(), df, account_value=2000, liquidity_rank=80)
        self.assertTrue({"likidite", "likidite_sira", "yogunlasma"} <= rules(out))

    def test_stale_and_unconfirmed_data(self):
        df = candles([10.0] * 40)
        out = evaluate_position(
            "paper", "SKBNK.IS", 1, df.index[0].date(), df,
            reference_day=(df.index[-1] + pd.Timedelta(days=10)).date(),
            unconfirmed_action="%40 bedelli (KAP ile teyit edilmeli)",
        )
        self.assertTrue({"veri", "veri_islem"} <= rules(out))

    def test_account_drawdown(self):
        eq = pd.Series([100, 120, 100], index=pd.bdate_range("2026-01-05", periods=3), dtype=float)
        self.assertEqual([a.rule for a in evaluate_account("paper", eq)], ["hesap_dusus"])
        self.assertEqual(evaluate_account("paper", eq.iloc[:2]), [])


class NoLookaheadTest(unittest.TestCase):
    def test_future_candles_do_not_change_alerts(self):
        rng = np.random.default_rng(3)
        closes = 100 * np.exp(np.cumsum(rng.normal(0, 0.03, 300)))
        df = candles(closes)
        cut = df.index[200].date()
        future = df.copy()
        future.loc[future.index > df.index[200], ["open", "high", "low", "close"]] *= 3
        a = evaluate_position("paper", "X.IS", 10, df.index[50].date(), df, as_of=cut)
        b = evaluate_position("paper", "X.IS", 10, df.index[50].date(), future, as_of=cut)
        self.assertEqual(a, b)
        self.assertTrue(all(x.data_date == cut for x in a))


class LogTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "alerts.csv"
        df = candles([100.0] * 30 + [120.0] * 10 + [100.0])
        self.alerts = evaluate_position("paper", "X.IS", 10, df.index[0].date(), df)

    def tearDown(self):
        self.tmp.cleanup()

    def test_sent_once_then_closed(self):
        first = update_alert_log(self.alerts, D("2026-03-02"), self.path)
        self.assertEqual({e for e, _ in first}, {"open"})
        again = update_alert_log(self.alerts, D("2026-03-03"), self.path)
        self.assertEqual(again, [])
        gone = update_alert_log([], D("2026-03-04"), self.path)
        self.assertEqual({e for e, _ in gone}, {"close"})
        self.assertEqual(open_alerts(self.path), {})

    def test_escalation_is_reported(self):
        from dataclasses import replace

        update_alert_log([replace(self.alerts[0], severity=2)], D("2026-03-02"), self.path)
        events = update_alert_log([replace(self.alerts[0], severity=3)], D("2026-03-03"), self.path)
        self.assertEqual([e for e, _ in events], ["escalate"])

    def test_thresholds_are_in_one_place(self):
        self.assertEqual(cfg.STOP_ATR_MULTIPLE, 2.0)


if __name__ == "__main__":
    unittest.main()
