"""
Bağımsız doğrulama M15 (ORTA): if Yahoo later adjusts a split itself, our row in
data/corporate_actions.csv would adjust it a second time and create a fake jump. An action is
skipped when the raw ex-date open is a normal session (within BIST's ±10% limit) but applying the
factor would make it impossible (beyond the limit); the daily report names it.
"""

import unittest

import pandas as pd

from core.market import corrections as C


def frame(closes, first="2026-03-02"):
    index = pd.bdate_range(first, periods=len(closes))
    return pd.DataFrame({"open": closes, "high": closes, "low": closes, "close": closes, "volume": 1000.0},
                        index=index)


class DoubleAdjustmentTest(unittest.TestCase):
    def setUp(self):
        C.double_adjusted().clear()
        self.action = C.CorporateAction("AAA.IS", pd.Timestamp("2026-03-04").date(), kind="bonus", ratio=1.0,
                                        source="https://kap")

    def test_unadjusted_data_is_adjusted(self):
        df = C.apply_corporate_actions(frame([20.0, 20.0, 10.0, 10.0]), "AAA.IS", [self.action])
        self.assertEqual(list(df["close"]), [10.0, 10.0, 10.0, 10.0])
        self.assertEqual(df["volume"].iloc[0], 2000.0)
        self.assertEqual(C.double_adjusted(), {})

    def test_already_adjusted_data_is_left_alone_and_named(self):
        raw = frame([10.0, 10.0, 10.2, 10.1])  # Yahoo already halved the old prices
        df = C.apply_corporate_actions(raw, "AAA.IS", [self.action])
        self.assertEqual(list(df["close"]), list(raw["close"]))  # not 5 → 10.2 (+104%)
        (text,) = C.double_adjusted().values()
        self.assertIn("AAA", text)
        self.assertIn("04.03.2026", text)
        self.assertIn("uygulanmadı", text)

    def test_a_real_limit_move_on_a_small_factor_is_still_adjusted(self):
        small = C.CorporateAction("AAA.IS", pd.Timestamp("2026-03-04").date(), factor=0.97, source="x")
        df = C.apply_corporate_actions(frame([10.0, 10.0, 9.8, 9.8]), "AAA.IS", [small])
        self.assertAlmostEqual(df["close"].iloc[0], 9.7)  # 9.8/9.7 = +1%: possible, applied

    def test_a_future_dated_row_waits_for_its_session(self):
        # validation M15 D-3: a row entered before its ex-date rescaled today's prices early (11,0 → 6,0)
        later = C.CorporateAction("AAA.IS", pd.Timestamp("2026-03-10").date(), kind="bonus", ratio=1.0, source="x")
        raw = frame([10.0, 10.5, 11.0])
        df = C.apply_corporate_actions(raw, "AAA.IS", [later])
        self.assertEqual(list(df["close"]), [10.0, 10.5, 11.0])
        self.assertEqual(C.double_adjusted(), {})

    def test_the_daily_report_shows_it(self):
        from core.reports import daily

        C.double_adjusted()[("AAA.IS", "2026-03-04")] = "AAA 04.03.2026 bonus: uygulanmadı"
        self.assertIn("AAA 04.03.2026 bonus: uygulanmadı", daily.corporate_action_problems([]))


if __name__ == "__main__":
    unittest.main()
