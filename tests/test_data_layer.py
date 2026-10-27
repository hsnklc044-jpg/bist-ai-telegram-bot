import unittest
from datetime import datetime
from unittest import mock

import pandas as pd

from core.infrastructure.exceptions import MarketError
from core.market import calendar, data, provider, store
from tests.helpers import FakeProvider, make_ohlcv, offline_market

IST = calendar.ISTANBUL


class CalendarTest(unittest.TestCase):
    def test_before_close_uses_previous_session(self):
        now = datetime(2026, 10, 22, 15, 0, tzinfo=IST)  # Thursday afternoon
        self.assertEqual(str(calendar.last_final_session_date(now)), "2026-10-21")

    def test_after_close_uses_today(self):
        now = datetime(2026, 10, 22, 18, 30, tzinfo=IST)
        self.assertEqual(str(calendar.last_final_session_date(now)), "2026-10-22")

    def test_weekend_rolls_back_to_friday(self):
        now = datetime(2026, 10, 25, 12, 0, tzinfo=IST)  # Sunday
        self.assertEqual(str(calendar.last_final_session_date(now)), "2026-10-23")

    def test_monday_morning_uses_friday(self):
        now = datetime(2026, 10, 26, 10, 0, tzinfo=IST)
        self.assertEqual(str(calendar.last_final_session_date(now)), "2026-10-23")

    def test_open_candle_dropped(self):
        df = make_ohlcv(rows=5, end="2026-10-22")
        now = datetime(2026, 10, 22, 11, 0, tzinfo=IST)

        trimmed = calendar.drop_open_candle(df, now)

        self.assertEqual(len(trimmed), 4)
        self.assertEqual(str(trimmed.index[-1].date()), "2026-10-21")


class StoreTest(unittest.TestCase):
    def test_first_update_downloads_full_history(self):
        with offline_market() as fake:
            status = store.update(["AAA.IS"])

            self.assertEqual(status, {"AAA.IS": "full"})
            self.assertEqual(len(store.read("AAA.IS")), len(fake.frame("AAA.IS")))

    def test_second_update_is_skipped_then_incremental(self):
        with offline_market() as fake:
            store.update(["AAA.IS"])
            self.assertEqual(store.update(["AAA.IS"]), {"AAA.IS": "fresh"})

            later = datetime.now() + pd.Timedelta(hours=1)
            status = store.update(["AAA.IS"], now=later)

            self.assertEqual(status, {"AAA.IS": "incremental"})
            self.assertEqual(len(fake.calls), 2)
            self.assertGreater(fake.calls[1][1], fake.calls[0][1])

    def test_times_with_and_without_time_zone_mix_safely(self):
        # one caller passes Istanbul time, another the computer's local time: the refresh check
        # must compare them as the same clock instead of failing with a TypeError
        with offline_market():
            aware = datetime(2026, 10, 24, 12, 0, tzinfo=IST)

            def local(minutes):  # the same moment as this computer's clock shows it, without a zone
                return (aware + pd.Timedelta(minutes=minutes)).astimezone().replace(tzinfo=None)

            store.update(["AAA.IS"], now=aware)
            self.assertEqual(store.update(["AAA.IS"], now=local(5)), {"AAA.IS": "fresh"})
            self.assertEqual(store.update(["AAA.IS"], now=local(60)), {"AAA.IS": "incremental"})
            self.assertEqual(store.update(["AAA.IS"], now=aware + pd.Timedelta(minutes=65)), {"AAA.IS": "fresh"})

    def test_adjusted_history_is_replaced(self):
        with offline_market() as fake:
            store.update(["AAA.IS"])

            adjusted = fake.frame("AAA.IS").copy()
            adjusted[["open", "high", "low", "close"]] *= 0.9  # dividend adjustment
            fake.overrides["AAA.IS"] = adjusted

            later = datetime.now() + pd.Timedelta(hours=1)
            status = store.update(["AAA.IS"], now=later)

            self.assertEqual(status, {"AAA.IS": "readjusted"})
            stored = store.read("AAA.IS")
            self.assertAlmostEqual(stored["close"].iloc[0], adjusted["close"].iloc[0], places=6)

    def test_provider_failure_keeps_stored_data(self):
        with offline_market() as fake:
            store.update(["AAA.IS"])
            fake.fail = True

            later = datetime.now() + pd.Timedelta(hours=1)
            self.assertEqual(store.update(["AAA.IS"], now=later), {"AAA.IS": "failed"})

            data.clear_cache()
            with mock.patch.object(store, "REFRESH_MINUTES", 0):
                df = data.load_price_history("AAA.IS")

            self.assertFalse(df.empty)

    def test_unknown_symbol_raises(self):
        fake = FakeProvider()
        fake.overrides["NONE.IS"] = make_ohlcv(rows=0)

        with offline_market(fake), self.assertRaises(MarketError):
            data.load_price_history("NONE.IS")


class DataTest(unittest.TestCase):
    def test_default_period_has_long_history(self):
        with offline_market():
            df = data.load_price_history("THYAO.IS")

        self.assertGreaterEqual(len(df), 450)
        self.assertEqual(list(df.columns), list(provider.COLUMNS))

    def test_returned_frame_is_a_copy(self):
        with offline_market():
            df = data.load_price_history("THYAO.IS")
            df["close"] = 0
            again = data.load_price_history("THYAO.IS")

        self.assertGreater(again["close"].iloc[-1], 0)

    def test_period_window(self):
        with offline_market():
            df = data.load_price_history("THYAO.IS", period="6mo")

        span = (df.index[-1] - df.index[0]).days
        self.assertTrue(150 <= span <= 183)


class YahooParsingTest(unittest.TestCase):
    def test_multi_ticker_frame(self):
        a = make_ohlcv(rows=3, seed=1)
        b = make_ohlcv(rows=3, seed=2)
        a.columns = [c.title() for c in a.columns]
        b.columns = [c.title() for c in b.columns]
        raw = pd.concat({"AAA.IS": a, "BBB.IS": b}, axis=1)
        raw.index = raw.index.tz_localize("Europe/Istanbul")

        with mock.patch.object(provider.yf, "download", return_value=raw):
            result = provider.YahooProvider().fetch(
                ["AAA.IS", "BBB.IS", "CCC.IS"], pd.Timestamp("2026-01-01").date()
            )

        self.assertEqual(sorted(result), ["AAA.IS", "BBB.IS"])
        self.assertIsNone(result["AAA.IS"].index.tz)
        self.assertEqual(list(result["AAA.IS"].columns), list(provider.COLUMNS))
