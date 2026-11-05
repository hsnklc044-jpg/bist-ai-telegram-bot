"""
K-78 pre-tests (DECISIONS K-78 §13), synthetic data only; no factor result and no return of real data.
- double adjustment: a split the provider already adjusted is not applied a second time; a raw one once;
- the factors use only prices up to the formation day;
- the slice: floor(n/3), ties by code;
- applicability: an upper-limit open, a missing entry day and a stock that stops trading are treated
  the same in the slice and in the universe;
- coverage counts per month.
"""

import math
import unittest
from datetime import date

import numpy as np
import pandas as pd

from core.analytics import factor_study as F
from core.market.corrections import CorporateAction


def bars(n=400, end="2024-05-31", seed=0, volume=1e6, start_price=100.0):
    from core.market.calendar import is_session_day

    days = [d for d in pd.bdate_range(end=end, periods=int(n * 1.1)) if is_session_day(d.date())][-n:]
    rng = np.random.default_rng(seed)
    close = start_price * np.exp(np.cumsum(rng.normal(0, 0.01, len(days))))
    return pd.DataFrame({"open": close, "high": close * 1.01, "low": close * 0.99, "close": close,
                         "volume": float(volume)}, index=pd.DatetimeIndex(days))


def split_at(df, ex, factor):
    out = df.copy()
    after = out.index >= pd.Timestamp(ex)
    out.loc[after, ["open", "high", "low", "close"]] *= factor
    return out


class DoubleAdjustmentTest(unittest.TestCase):
    def setUp(self):
        self.base = bars()
        self.ex = self.base.index[200].date()
        self.action = CorporateAction("AAA.IS", self.ex, kind="bonus", ratio=1.0)  # 1:1 bonus, factor 0.5

    def test_raw_split_is_applied_once(self):
        raw = split_at(self.base, self.ex, 0.5)
        out, skipped = F.adjust(raw, [self.action])
        self.assertEqual(skipped, [])
        np.testing.assert_allclose(out["close"].to_numpy(), (self.base["close"] * 0.5).to_numpy())

    def test_provider_adjusted_split_is_not_applied_again(self):
        provider = self.base * [0.5, 0.5, 0.5, 0.5, 1.0]  # already adjusted: no jump left
        out, skipped = F.adjust(provider, [self.action])
        self.assertEqual(len(skipped), 1)
        self.assertIn("sıçrama yok", skipped[0])
        pd.testing.assert_frame_equal(out, provider)

    def test_same_action_listed_twice_is_still_applied_once(self):
        raw = split_at(self.base, self.ex, 0.5)
        out, skipped = F.adjust(raw, [self.action, self.action])
        self.assertEqual(len(skipped), 1)  # the second finds no jump left
        np.testing.assert_allclose(out["close"].to_numpy(), (self.base["close"] * 0.5).to_numpy())


class FactorTest(unittest.TestCase):
    def test_momentum_and_volatility_windows(self):
        close = pd.Series(np.arange(1.0, 301.0))
        self.assertAlmostEqual(F.momentum(close), close.iloc[-22] / close.iloc[-253] - 1)
        logs = np.log(close.iloc[-253:]).diff().dropna()
        self.assertAlmostEqual(F.volatility(close), float(logs.std(ddof=1)))
        self.assertTrue(math.isnan(F.momentum(close.iloc[:252])))
        self.assertTrue(math.isnan(F.volatility(close.iloc[:252])))

    def test_no_price_after_formation_is_used(self):
        df = bars(n=420, end="2024-07-31")
        frames = {f"S{i:02d}.IS": df * (1 + i / 100) for i in range(3)}
        day = date(2024, 5, 31)
        changed = {s: f.copy() for s, f in frames.items()}
        entry = pd.Timestamp(F.next_session(F.market_days(frames), day))
        for f in changed.values():
            f.loc[f.index > entry, ["open", "close"]] *= 3  # after the entry open: the future
        a = F.month(frames, day, set(frames))
        b = F.month(changed, day, set(frames))
        self.assertEqual(a.slices, b.slices)

    def test_slice_is_a_third_with_ties_by_code(self):
        values = {"D.IS": 1.0, "A.IS": 1.0, "C.IS": 2.0, "B.IS": 0.5, "E.IS": 0.1, "F.IS": 3.0, "G.IS": 1.0}
        self.assertEqual(F.chosen(values, low=False), ["F.IS", "C.IS"])
        self.assertEqual(F.chosen(values, low=True), ["E.IS", "B.IS"])
        self.assertEqual(F.chosen({"B.IS": 1.0, "A.IS": 1.0, "C.IS": 1.0}, low=False), ["A.IS"])


class ApplicabilityTest(unittest.TestCase):
    formation = date(2024, 5, 31)

    def frames(self, n=90):
        out = {}
        for i in range(n):
            df = bars(n=300, end="2024-06-28", seed=i, volume=1e6 * (i + 1))
            out[f"S{i:02d}.IS"] = df
        return out

    def test_limit_up_open_and_missing_entry_leave_slice_and_universe_alike(self):
        frames = self.frames()
        entry = pd.Timestamp(F.next_session(F.market_days(frames), self.formation))
        plain = F.month(frames, self.formation, set(frames))
        top = plain.slices["momentum"][0]
        low = plain.slices["dusuk_oynaklik"][0]
        prev = frames[top].loc[frames[top].index < entry, "close"].iloc[-1]
        frames[top].loc[entry, "open"] = prev * 1.10
        frames[low] = frames[low].drop(index=entry)
        m = F.month(frames, self.formation, set(frames))
        self.assertEqual(m.not_applicable, {top: "tavan açılış", low: "giriş günü veri yok"})
        for gone in (top, low):
            self.assertNotIn(gone, m.universe)
            for picked in m.slices.values():
                self.assertNotIn(gone, picked)
        self.assertEqual(len(m.universe), len(plain.universe) - 2)

    def test_stock_that_stops_trading_exits_at_its_last_close(self):
        df = bars(n=300, end="2024-06-28")
        entry = F.next_session(F.market_days({'A': df}), self.formation)
        stopped = df.loc[: "2024-06-14"]
        self.assertEqual(F.exit_close(stopped, entry, date(2024, 6, 28)),
                         (date(2024, 6, 14), float(stopped["close"].iloc[-1])))
        self.assertEqual(F.exit_close(df, entry, date(2024, 6, 28))[0], df.index[-1].date())

    def test_liquidity_cut_and_validity(self):
        m = F.month(self.frames(), self.formation, set(self.frames()))
        self.assertEqual(m.liquidity_out, 18)  # 20% of 90, the lowest turnover first
        self.assertEqual(len(m.universe), 72)
        self.assertTrue(m.valid)
        small = F.month(self.frames(70), self.formation, set(self.frames(70)))
        self.assertFalse(small.valid)  # 70 usable members < 80

    def test_member_without_price_is_counted(self):
        frames = self.frames()
        m = F.month(frames, self.formation, set(frames) | {"YOK.IS"})
        self.assertEqual((m.members, m.no_price), (91, 1))

    def test_next_session_skips_weekend_and_holidays(self):
        days = F.market_days({"A": bars(n=300, end="2024-06-28")})
        self.assertEqual(F.next_session(days, date(2024, 5, 31)), date(2024, 6, 3))
        self.assertIsNone(F.next_session(days, date(2024, 6, 28)))

    def test_a_day_no_stock_traded_is_a_holiday_not_missing_data(self):
        """Pre-test finding 05.11.2026: the holiday file starts in 2026; 01.05.2023 etc. were not in it."""

        frames = self.frames()
        holiday = pd.Timestamp(F.market_days(frames)[F.market_days(frames) > pd.Timestamp(self.formation)][0])
        closed = {s: df.drop(index=holiday) for s, df in frames.items()}
        m = F.month(closed, self.formation, set(closed))
        self.assertEqual(m.not_applicable, {})
        self.assertEqual(len(m.universe), 72)


class CoverageTest(unittest.TestCase):
    def test_counts_only(self):
        frames = {f"S{i:02d}.IS": bars(n=400, end="2023-01-31", seed=i, volume=1e6 * (i + 1)) for i in range(90)}
        table = F.coverage(frames, members_on=lambda d: {s.removesuffix(".IS") for s in frames})
        self.assertEqual(list(table["formasyon"]), F.formation_days(frames))
        self.assertTrue({"uye", "fiyatsiz", "kullanilabilir", "likidite_disi", "tavan_acilis", "giris_verisi_yok",
                         "evren", "dilim_momentum", "dilim_dusuk_oynaklik", "gecerli"} <= set(table.columns))
        self.assertFalse(any("getiri" in c for c in table.columns))
        self.assertTrue((table["formasyon"] >= F.FIRST_FORMATION).all())


if __name__ == "__main__":
    unittest.main()


class MainTest(unittest.TestCase):
    def test_kapsam_prints_counts_only(self):
        import tempfile
        from contextlib import redirect_stdout
        from io import StringIO
        from pathlib import Path
        from unittest import mock

        from core.analytics import provenance as P

        frames = {f"S{i:02d}.IS": bars(n=400, end="2023-01-31", seed=i, volume=1e6 * (i + 1)) for i in range(5)}
        with tempfile.TemporaryDirectory() as tmp:
            P.freeze(frames, Path(tmp) / "d", None)
            with mock.patch("core.market.membership.members_on", lambda d: {s[:3] for s in frames}), \
                    redirect_stdout(StringIO()) as out:
                self.assertEqual(F.main(["kapsam", str(Path(tmp) / "d")]), 0)
                self.assertEqual(F.main(["yanlis"]), 2)
        text = out.getvalue()
        self.assertIn("Geçerli ay: 0", text)
        self.assertIn("faktör değeri ve getiri gösterilmedi", text)
