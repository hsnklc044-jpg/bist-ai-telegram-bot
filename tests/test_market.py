import unittest

from core.infrastructure.exceptions import MarketError
from core.market.indicators import generate_indicator_snapshot
from core.market.models import MarketTrend
from tests.helpers import FakeProvider, make_ohlcv, offline_market


class IndicatorTest(unittest.TestCase):
    def test_snapshot_values_are_sane(self):
        with offline_market():
            snap = generate_indicator_snapshot("THYAO.IS")

        self.assertGreater(snap.price, 0)
        self.assertTrue(0 <= snap.rsi <= 100)
        self.assertGreater(snap.atr, 0)
        self.assertLess(snap.bollinger_lower, snap.bollinger_upper)
        self.assertIsInstance(snap.trend, MarketTrend)
        self.assertIsNotNone(snap.ema200)
        self.assertIsNotNone(snap.sma200)

    def test_short_history_has_no_long_term_average(self):
        fake = FakeProvider()
        fake.overrides["NEW.IS"] = make_ohlcv(rows=120, seed=3)

        with offline_market(fake):
            snap = generate_indicator_snapshot("NEW.IS")

        self.assertIsNone(snap.ema200)
        self.assertIsNone(snap.sma200)

    def test_too_short_history_is_rejected_not_zeroed(self):
        fake = FakeProvider()
        fake.overrides["IPO.IS"] = make_ohlcv(rows=30, seed=4)

        with offline_market(fake), self.assertRaises(MarketError):
            generate_indicator_snapshot("IPO.IS")

    def test_analyze_stock_trade_levels(self):
        from core.analytics.analyzer import analyze_stock

        with offline_market():
            result = analyze_stock("EREGL.IS")

        self.assertIsNotNone(result)
        self.assertLess(result["stop_loss"], result["entry_price"])
        self.assertLess(result["entry_price"], result["target_1"])
        self.assertLess(result["target_1"], result["target_2"])

    def test_analyze_stock_skips_short_history(self):
        from core.analytics.analyzer import analyze_stock

        fake = FakeProvider()
        fake.overrides["IPO.IS"] = make_ohlcv(rows=30, seed=4)

        with offline_market(fake):
            self.assertIsNone(analyze_stock("IPO.IS"))


class QualityTest(unittest.TestCase):
    def test_detects_gaps_jumps_and_staleness(self):
        from core.market.quality import check_symbol

        bench = make_ohlcv(rows=300, seed=1)
        df = make_ohlcv(rows=300, seed=2).iloc[:-2]  # two days stale
        df = df.drop(df.index[100:103])  # three missing days
        df.loc[df.index[200], "close"] = df["close"].iloc[199] * 1.5  # +50% jump
        df.loc[df.index[200], "high"] = df.loc[df.index[200], "close"]
        df.loc[df.index[50], "volume"] = 0

        q = check_symbol(df, "X.IS", bench.index)

        self.assertEqual(q.missing, 3)
        self.assertEqual(q.stale_days, 2)
        self.assertEqual(q.zero_volume, 1)
        self.assertTrue(any("+50" in str(j) for j in q.jumps))
        self.assertAlmostEqual(q.jumps[0].suggested_factor, 1.5, places=2)
        self.assertFalse(q.ok)

    def test_clean_series_is_ok(self):
        from core.market.quality import check_symbol

        bench = make_ohlcv(rows=300, seed=1, vol=0.01)
        q = check_symbol(make_ohlcv(rows=300, seed=2, vol=0.01), "Y.IS", bench.index)

        self.assertTrue(q.ok, q)


class UniverseTest(unittest.TestCase):
    def test_universe_file_is_normalized(self):
        import pathlib
        import tempfile
        from unittest import mock

        from core.market import universe

        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "u.csv"
            path.write_text("symbol,name\nthyao,THY\nTHYAO.IS,dup\n eregl ,Ereğli\n\n", "utf-8")

            with mock.patch.object(universe, "UNIVERSE_FILE", path):
                self.assertEqual(universe.load_universe(), ["THYAO.IS", "EREGL.IS"])

    def test_shipped_universe_loads(self):
        from core.market.universe import load_universe

        symbols = load_universe()

        self.assertGreaterEqual(len(symbols), 10)
        self.assertTrue(all(s.endswith(".IS") for s in symbols))


class ApplySuggestionsTest(unittest.TestCase):
    def test_writes_rows_once(self):
        import pathlib
        import tempfile

        from core.market.corrections import load_corporate_actions
        from core.market.quality import apply_suggestions, check_symbol

        df = make_ohlcv(rows=100, seed=2, vol=0.005)
        df.loc[df.index[60]:, ["open", "high", "low", "close"]] /= 3  # unadjusted 1:3
        report = [check_symbol(df, "X.IS")]

        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "ca.csv"
            self.assertEqual(apply_suggestions(report, path), 1)
            self.assertEqual(apply_suggestions(report, path), 0)
            actions = load_corporate_actions(path)

        self.assertEqual(len(actions), 1)
        self.assertAlmostEqual(actions[0].factor, 1 / 3, places=2)

    def test_ten_to_twenty_percent_moves_not_flagged(self):
        from core.market.quality import check_symbol

        df = make_ohlcv(rows=100, seed=3, vol=0.005)
        df.loc[df.index[50]:, ["open", "high", "low", "close"]] *= 1.15

        self.assertEqual(check_symbol(df, "Y.IS").jumps, [])
