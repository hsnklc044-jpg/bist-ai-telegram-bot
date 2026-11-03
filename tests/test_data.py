"""
Data and indicator layer (03.11.2026 request): the BIST 30 list, the hourly loader (no network:
a fake yfinance download), the extended indicators against hand computations and the library,
and the "dip dönüşü" trigger's truth table.
"""

import csv
import unittest

import numpy as np
import pandas as pd

from core.config.bist30 import BIST30_TICKERS
from core.config.paths import DATA_DIR
from core.market import extended as X
from core.market import hourly as H

NOW = pd.Timestamp("2026-11-03 18:30", tz=H.ISTANBUL)


def hourly(n=300, seed=1, start="2026-06-01 07:00"):
    """Hourly candles in UTC as yfinance returns them."""

    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.006, n)))
    prev = np.r_[close[0], close[:-1]]
    open_ = prev * (1 + rng.normal(0, 0.001, n))
    high = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, 0.002, n)))
    low = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, 0.002, n)))
    index = pd.date_range(start, periods=n, freq="h", tz="UTC")
    return pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close,
                         "Volume": rng.integers(1e5, 1e6, n).astype(float)}, index=index)


class ListTest(unittest.TestCase):
    def test_bist30(self):
        self.assertEqual(len(BIST30_TICKERS), 30)
        self.assertEqual(len(set(BIST30_TICKERS)), 30)
        self.assertTrue(all(t.endswith(".IS") and t[:-3].isalpha() and t[:-3].isupper() for t in BIST30_TICKERS))
        with open(DATA_DIR / "bist30.csv", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual([f"{r['symbol']}.IS" for r in rows], BIST30_TICKERS)  # one list, two places
        self.assertTrue(all(r["source"] for r in rows))
        from core.screen import universe

        self.assertEqual(universe.symbols("bist30"), BIST30_TICKERS)  # /tara evren=bist30


class CleanTest(unittest.TestCase):
    def test_bad_rows_go_and_time_is_istanbul(self):
        raw = hourly(10)
        raw.iloc[2, 0] = np.nan  # NaN open
        raw.iloc[3, 3] = 0.0  # zero close
        raw.iloc[4, raw.columns.get_loc("High")] = raw.iloc[4]["Low"] * 0.9  # high < low
        raw = pd.concat([raw, raw.iloc[[5]]])  # duplicate stamp
        out = H.clean(raw, NOW)
        self.assertEqual(len(out), 7)
        self.assertEqual(list(out.columns), list(H.COLUMNS))
        self.assertEqual(str(out.index.tz), H.ISTANBUL)
        self.assertEqual(out.index[0].hour, 10)  # 07:00 UTC = 10:00 Istanbul
        self.assertTrue(out.index.is_monotonic_increasing and out.index.is_unique)

    def test_open_hour_is_dropped_and_empty_is_safe(self):
        raw = hourly(3, start="2026-11-03 13:00")  # 16:00, 17:00, 18:00 Istanbul
        self.assertEqual(len(H.clean(raw, NOW)), 2)  # the 18:00 candle is still open at 18:30
        for bad in (None, pd.DataFrame(), pd.DataFrame({"x": [1]})):
            self.assertTrue(H.clean(bad, NOW).empty)


class LoaderTest(unittest.TestCase):
    def fake(self, failures=0, present=("AKBNK.IS", "GARAN.IS")):
        calls = []

        def download(tickers, **kw):
            calls.append(kw)
            if len(calls) <= failures:
                raise ConnectionError("internet yok")
            return pd.concat({t: hourly(50, seed=i) for i, t in enumerate(present)}, axis=1)

        return download, calls

    def test_batch_download_and_missing_reported(self):
        download, calls = self.fake()
        data = H.load_hourly(["AKBNK.IS", "GARAN.IS", "EKOY.IS"], download=download, now=NOW)
        self.assertEqual(sorted(data.frames), ["AKBNK.IS", "GARAN.IS"])
        self.assertEqual(data.missing, {"EKOY.IS": "veri yok"})
        self.assertEqual((calls[0]["interval"], calls[0]["period"]), ("1h", "1y"))
        self.assertEqual(len(calls), 2)  # one batched request, then the missing one alone
        self.assertIn("EKOY.IS (veri yok)", data.summary())

    def test_a_ticker_empty_in_the_batch_is_asked_alone(self):
        # 03.11.2026: ISCTR.IS came back empty in the 30-ticker batch but complete on its own
        calls = []

        def download(tickers, **kw):
            calls.append(tickers)
            if len(tickers) > 1:
                return pd.concat({"AKBNK.IS": hourly(50)}, axis=1)
            return pd.concat({tickers[0]: hourly(50, seed=4)}, axis=1)

        data = H.load_hourly(["AKBNK.IS", "ISCTR.IS"], download=download, now=NOW, sleep=lambda s: None)
        self.assertEqual(sorted(data.frames), ["AKBNK.IS", "ISCTR.IS"])
        self.assertEqual(calls[1], ["ISCTR.IS"])
        self.assertEqual(data.missing, {})

    def test_retries_then_reports(self):
        download, calls = self.fake(failures=2)
        data = H.load_hourly(["AKBNK.IS"], download=download, now=NOW, sleep=lambda s: None)
        self.assertEqual((len(calls), list(data.frames)), (3, ["AKBNK.IS"]))
        download, calls = self.fake(failures=9)
        data = H.load_hourly(["AKBNK.IS"], download=download, now=NOW, sleep=lambda s: None)
        self.assertEqual((data.frames, data.missing), ({}, {"AKBNK.IS": "indirme başarısız"}))


class IndicatorTest(unittest.TestCase):
    def setUp(self):
        self.df = H.clean(hourly(400), NOW)
        self.ind = X.add_indicators(self.df)

    def test_by_hand_and_library(self):
        from ta.momentum import RSIIndicator, StochasticOscillator

        c, h, low, v = self.df["close"], self.df["high"], self.df["low"], self.df["volume"]
        ema50 = c.ewm(span=50, adjust=False).mean()
        pd.testing.assert_series_equal(self.ind["ema50_uzaklik"].iloc[60:], ((c / ema50 - 1) * 100).iloc[60:],
                                       check_names=False)
        pd.testing.assert_series_equal(self.ind["rsi"], RSIIndicator(c, 14).rsi(), check_names=False)
        fast = StochasticOscillator(h, low, c, 14, 3).stoch()
        pd.testing.assert_series_equal(self.ind["stoch_k"], fast.rolling(3).mean(), check_names=False)
        pd.testing.assert_series_equal(self.ind["stoch_d"], fast.rolling(3).mean().rolling(3).mean(),
                                       check_names=False)
        band = (c - self.ind["bb_alt"]) / (self.ind["bb_ust"] - self.ind["bb_alt"])
        np.testing.assert_allclose(self.ind["bb_yuzde"].iloc[30:], band.iloc[30:])
        mfm = (((c - low) - (h - c)) / (h - low)).fillna(0.0)
        np.testing.assert_allclose(self.ind["cmf"].iloc[30:], ((mfm * v).rolling(20).sum() / v.rolling(20).sum()
                                                               * 100).iloc[30:])
        self.assertTrue(self.ind["adx"].iloc[:28].isna().all())  # warm-up is unknown, not 0
        self.assertTrue(self.ind["ema200"].iloc[-1] > 0)

    def test_no_look_ahead(self):
        changed = self.df.copy()
        changed.iloc[300:] *= 1.5
        after = X.add_indicators(changed)
        cols = [c for c in self.ind.columns if c not in self.df.columns]
        pd.testing.assert_frame_equal(self.ind[cols].iloc[:300], after[cols].iloc[:300])

    def test_bad_input(self):
        self.assertTrue(X.add_indicators(pd.DataFrame()).empty)
        self.assertEqual(list(X.add_indicators(pd.DataFrame({"close": [1.0]})).columns), ["close"])


class TriggerTest(unittest.TestCase):
    def test_truth_table(self):
        frame = pd.DataFrame({
            "rsi":       [40, 30, 40, 30, 30, 30, np.nan],
            "stoch_k":   [50, 50, 15, 50, 50, 50, 10],
            "bb_yuzde":  [0.05, 0.05, 0.05, 0.30, 0.05, 0.05, 0.05],
            "macd_hist": [-0.8, -0.5, -0.4, -0.3, -0.5, 0.1, 0.2],
        })
        # row 0: not oversold; 1: rsi<35, near band, hist rising below zero -> True;
        # 2: stoch<20 -> True; 3: far from the band; 4: hist falling; 5: hist above zero; 6: NaN hist history
        self.assertEqual(list(X.trigger_mask(frame)), [False, True, True, False, False, False, False])

    def test_scan(self):
        frames = {"A.IS": H.clean(hourly(300, seed=5), NOW)}
        found = X.scan(frames)
        self.assertEqual(list(found.columns), ["symbol", "time", "close", "rsi", "stoch_k", "bb_yuzde", "macd_hist"])
        mask = X.trigger_mask(X.add_indicators(frames["A.IS"]))
        self.assertEqual(len(found), int(mask.iloc[-1]))


if __name__ == "__main__":
    unittest.main()
