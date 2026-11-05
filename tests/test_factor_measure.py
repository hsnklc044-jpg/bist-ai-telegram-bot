"""
K-78 measurement rules on synthetic data only (no real return is computed by these tests): holding
prices, turnover cost, the bootstrap, the verdict with its pre-written conditions and the two-download
table.
"""

import math
import unittest
from datetime import date

import numpy as np
import pandas as pd

from core.analytics import factor_measure as M


def flat(days, price=100.0):
    return pd.DataFrame({"open": price, "high": price, "low": price, "close": price, "volume": 1e6},
                        index=pd.DatetimeIndex(days))


class HoldingTest(unittest.TestCase):
    def test_entry_open_to_month_end_close(self):
        days = pd.bdate_range("2024-06-03", "2024-07-05")
        df = flat(days)
        df.loc["2024-06-03", "open"] = 100.0
        df.loc["2024-06-28", "close"] = 110.0
        got, notes = M.holding({"A": df}, ["A"], date(2024, 6, 3), pd.DatetimeIndex(days))
        self.assertAlmostEqual(got["A"], 0.10)
        self.assertEqual(notes, [])


class CostTest(unittest.TestCase):
    def test_first_month_buys_everything(self):
        self.assertAlmostEqual(M.cost(["A", "B"], []), 0.0015)

    def test_same_names_cost_nothing(self):
        self.assertEqual(M.cost(["A", "B"], ["B", "A"]), 0)

    def test_half_replaced(self):
        self.assertAlmostEqual(M.cost(["A", "C"], ["A", "B"]), 0.0015 * 0.5 + 0.0015 * 0.5)

    def test_higher_cost_line(self):
        self.assertAlmostEqual(M.cost(["A"], [], M.COST_INFO, M.COST_INFO), 0.003)


class BootstrapTest(unittest.TestCase):
    def test_same_seed_same_draws_and_length(self):
        x = np.arange(48.0)
        a, b = M.block_bootstrap(x, draws=500), M.block_bootstrap(x, draws=500)
        np.testing.assert_array_equal(a, b)
        self.assertEqual(len(a), 500)

    def test_constant_series_gives_point_interval(self):
        means = M.block_bootstrap(np.full(48, 0.01), draws=200)
        np.testing.assert_allclose(means, 0.01)


def series_of(excess, slice_net=None, universe_net=None, start="2022-11"):
    months = list(pd.period_range(start, periods=len(excess), freq="M"))
    s = M.Series(months=months, excess=list(excess), excess_high_cost=list(np.asarray(excess) - 0.001))
    s.slice_net = list(slice_net) if slice_net is not None else list(excess)
    s.universe_net = list(universe_net) if universe_net is not None else [0.0] * len(excess)
    return s


def noise(sd, seed=1, n=48):
    """Zero-mean noise from its own seed: the result never depends on test order (slow-machine shuffles)."""

    x = np.random.default_rng(seed).normal(0, sd, n)
    return x - x.mean()


class JudgeTest(unittest.TestCase):

    def test_too_few_months_is_unmeasured(self):
        v = M.judge("momentum", series_of([0.01] * 35), draws=200)
        self.assertEqual(v.label, M.UNMEASURED)

    def test_clear_effect_passes(self):
        v = M.judge("momentum", series_of(0.02 + noise(0.01)), draws=1000)
        self.assertEqual(v.label, M.PASSED, v.reasons)

    def test_tight_zero_excludes_literature_effect(self):
        v = M.judge("momentum", series_of(noise(0.002)), draws=1000)
        self.assertEqual(v.label, M.EXCLUDED)
        self.assertLess(v.upper, M.LITERATURE)

    def test_wide_noise_is_unanswered(self):
        v = M.judge("momentum", series_of(noise(0.05)), draws=1000)
        self.assertEqual(v.label, M.UNANSWERED)

    def test_years_condition(self):
        x = np.r_[np.full(2, 0.0), np.full(12, 0.08), np.full(12, -0.01), np.full(12, -0.01), np.full(10, 0.01)]
        v = M.judge("momentum", series_of(x), draws=1000)  # 2023 positive only
        self.assertEqual(v.years_positive, 1)
        self.assertNotEqual(v.label, M.PASSED)
        self.assertTrue(any("pozitif yıl" in r for r in v.reasons))

    def test_condition_failure_with_a_clear_interval_is_not_low_power(self):
        x = 0.02 + noise(0.01)
        wild = M.judge("dusuk_oynaklik", series_of(x, slice_net=x * 3, universe_net=x), draws=1000)
        self.assertGreater(wild.lower, 0)
        self.assertEqual(wild.label, M.FAILED_CONDITION)
        years = np.r_[np.full(2, 0.0), np.full(12, 0.12), np.full(12, -0.001), np.full(12, -0.001), np.full(10, 0.01)]
        v = M.judge("momentum", series_of(years), draws=1000)
        self.assertGreater(v.lower, 0)
        self.assertEqual(v.label, M.FAILED_CONDITION)

    def test_low_volatility_also_needs_lower_risk(self):
        x = 0.02 + noise(0.01)
        calm = M.judge("dusuk_oynaklik", series_of(x, slice_net=x, universe_net=x * 3), draws=1000)
        self.assertEqual(calm.label, M.PASSED)
        wild = M.judge("dusuk_oynaklik", series_of(x, slice_net=x * 3, universe_net=x), draws=1000)
        self.assertNotEqual(wild.label, M.PASSED)
        self.assertFalse(wild.lower_risk)


class CombineTest(unittest.TestCase):
    def v(self, label):
        return M.Verdict(factor="momentum", months=48, label=label)

    def test_table(self):
        self.assertEqual(M.combine(self.v(M.PASSED), self.v(M.PASSED)), M.PASSED)
        self.assertEqual(M.combine(self.v(M.PASSED), self.v(M.UNANSWERED)), M.SENSITIVE)
        self.assertEqual(M.combine(self.v(M.EXCLUDED), self.v(M.EXCLUDED)), M.EXCLUDED)
        self.assertEqual(M.combine(self.v(M.EXCLUDED), self.v(M.UNANSWERED)), M.UNANSWERED)
        self.assertEqual(M.combine(self.v(M.UNMEASURED), self.v(M.PASSED)), M.UNMEASURED)
        self.assertEqual(M.combine(self.v(M.FAILED_CONDITION), self.v(M.FAILED_CONDITION)), M.FAILED_CONDITION)
        self.assertEqual(M.combine(self.v(M.FAILED_CONDITION), self.v(M.UNANSWERED)), M.UNANSWERED)


class SeriesTest(unittest.TestCase):
    def test_end_to_end_on_synthetic_frames(self):
        from tests.test_factor_study import bars

        frames = {f"S{i:02d}.IS": bars(n=330, end="2023-03-31", seed=i, volume=1e6 * (i + 1)) for i in range(90)}
        out = M.series(frames, lambda d: {s.removesuffix(".IS") for s in frames}, stop=pd.Timestamp("2026-11-02"))
        for k, s in out.items():
            self.assertEqual(len(s.excess), len(s.months))
            self.assertTrue(all(math.isfinite(x) for x in s.excess))
            self.assertGreaterEqual(len(s.months), 1)  # at least one valid synthetic month was measured
        self.assertIn("momentum", M.text([M.judge("momentum", out["momentum"], draws=100)]))


if __name__ == "__main__":
    unittest.main()


class InformationTest(unittest.TestCase):
    def test_lines_and_counts(self):
        s = M.Series(months=list(pd.period_range("2024-01", periods=2, freq="M")), slice_net=[0.10, 0.20],
                     universe_net=[0.0, 0.0], excess=[0.1, 0.2], excess_high_cost=[0.1, 0.2],
                     benchmark=[0.05, math.nan], unmeasured=6, no_price=3, data_break=2, limit_open=1, no_entry=4,
                     notes=["a"])
        cpi = pd.DataFrame({"monthly_pct": [10.0]}, index=["2024-01"])
        line = M.information(s, cpi)
        self.assertIn("XU100'e göre aylık farkı %5.00 (1 ay)", line)
        self.assertIn("reel getirisi %0.00 (1 ay)", line)
        self.assertIn("ölçülemeyen ay 6; fiyatsız üye 3; veri kırığı 2; tavan açılış 1; giriş verisi yok 4; kilitli çıkış 1",
                      line)

    def test_no_data_is_said(self):
        s = M.Series(months=list(pd.period_range("2024-01", periods=1, freq="M")), slice_net=[0.1],
                     universe_net=[0.0], excess=[0.1], excess_high_cost=[0.1], benchmark=[math.nan])
        self.assertEqual(M.information(s, pd.DataFrame({"monthly_pct": []})).count("veri yok"), 2)


class FreshDownloadTest(unittest.TestCase):
    source = f"{M.FRESH_B} 2026-11-11 (123)"

    def setUp(self):
        from tests.test_factor_study import bars

        self.frames = {f"S{i:02d}.IS": bars(n=30, seed=i) for i in range(40)}

    def test_good_b_passes(self):
        self.assertEqual(M.check_b(self.source, date(2026, 11, 11), self.frames, self.frames), [])

    def test_store_snapshot_is_refused(self):
        self.assertIn("baştan indirme değil", M.check_b("yerel fiyat deposu (market.db)", date(2026, 11, 11),
                                                       self.frames, self.frames)[0])

    def test_typed_date_must_match_the_manifest(self):
        self.assertIn("aynı değil", M.check_b(self.source, date(2026, 11, 12), self.frames, self.frames)[0])

    def test_partial_download_is_refused(self):
        part = dict(list(self.frames.items())[:30])
        self.assertIn("B eksik", M.check_b(self.source, date(2026, 11, 11), self.frames, part)[0])

    def test_different_end_is_refused(self):
        short = {k: v.iloc[:-1] for k, v in self.frames.items()}
        self.assertIn("son tarihler farklı", M.check_b(self.source, date(2026, 11, 11), self.frames, short)[0])


class MainTest(unittest.TestCase):
    def test_pair_rules_stop_before_any_measurement(self):
        import tempfile
        from contextlib import redirect_stdout
        from io import StringIO
        from pathlib import Path
        from unittest import mock

        from core.analytics import provenance as P
        from tests.test_factor_study import bars

        frames = {"AAA.IS": bars(n=300, end="2023-01-31")}
        with tempfile.TemporaryDirectory() as tmp:
            P.freeze(frames, Path(tmp) / "a", None)
            P.freeze(frames, Path(tmp) / "b", None)
            args = [str(Path(tmp) / "a"), str(Path(tmp) / "b")]
            with redirect_stdout(StringIO()) as out, \
                    mock.patch.object(M, "series", side_effect=AssertionError("measured")):
                self.assertEqual(M.main([*args, "--tarih-a", "2026-11-04", "--tarih-b", "2026-11-06"]), 2)
                self.assertEqual(M.main([*args, "--tarih-a", "2026-11-04", "--tarih-b", "2026-11-11"]), 2)
            text = out.getvalue()
        self.assertIn("2 gün < 7", text)
        self.assertIn("56016f59", text)

    def test_prepare_cuts_the_holdout_and_the_common_start(self):
        from tests.test_factor_study import bars

        df = bars(n=300, end="2026-11-20")
        frames, skipped, breaks = M.prepare({"AAA.IS": df}, pd.Timestamp("2026-03-02"), actions=[])
        got = frames["AAA.IS"]
        self.assertGreaterEqual(got.index.min(), pd.Timestamp("2026-03-02"))
        self.assertLess(got.index.max(), pd.Timestamp("2026-11-02"))
        self.assertEqual((skipped, breaks), ([], {}))

    def test_measurement_runs_end_to_end_on_synthetic_snapshots(self):
        import tempfile
        from contextlib import redirect_stdout
        from io import StringIO
        from pathlib import Path
        from unittest import mock

        from core.analytics import provenance as P
        from tests.test_factor_study import bars

        frames = {f"S{i:02d}.IS": bars(n=330, end="2023-03-31", seed=i, volume=1e6 * (i + 1)) for i in range(90)}
        with tempfile.TemporaryDirectory() as tmp:
            P.freeze(frames, Path(tmp) / "a", None)
            P.freeze(frames, Path(tmp) / "b", None, source=f"{M.FRESH_B} 2026-11-11")
            with mock.patch.object(M, "DAILY_A", P.digest(frames)), \
                    mock.patch("core.market.membership.members_on", lambda d: {s[:3] for s in frames}), \
                    mock.patch.object(M, "DRAWS", 100), redirect_stdout(StringIO()) as out:
                self.assertEqual(M.main([str(Path(tmp) / "a"), str(Path(tmp) / "b"),
                                         "--tarih-a", "2026-11-04", "--tarih-b", "2026-11-11"]), 0)
        text = out.getvalue()
        self.assertIn("SONUÇ momentum: ÖLÇÜLEMEDİ", text)  # far fewer than 36 synthetic months
        self.assertIn("SONUÇ dusuk_oynaklik: ÖLÇÜLEMEDİ", text)
