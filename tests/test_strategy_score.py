import unittest

from core.strategy.score import score_frame
from tests.helpers import FakeProvider, make_ohlcv, offline_market


class ScoreParityTest(unittest.TestCase):
    """The historical score must equal what the live analyzer shows."""

    def test_last_row_matches_live_analyzer(self):
        from core.analytics.analyzer import analyze_stock
        from core.market import data

        for seed in range(8):
            with self.subTest(seed=seed):
                fake = FakeProvider()
                fake.overrides["P.IS"] = make_ohlcv(rows=600, seed=seed)

                with offline_market(fake):
                    live = analyze_stock("P.IS")
                    df = data.load_price_history("P.IS")

                hist = score_frame(df).iloc[-1]

                self.assertEqual(int(hist["score"]), live["score"])
                self.assertEqual(hist["signal"], live["signal"])
                self.assertEqual(hist["volume_ratio"], live["volume_ratio"])

    def test_no_lookahead(self):
        df = make_ohlcv(rows=300, seed=5)
        full = score_frame(df)
        cut = score_frame(df.iloc[:200])

        self.assertEqual(full["score"].iloc[199], cut["score"].iloc[-1])

    def test_warmup_rows_have_no_score(self):
        frame = score_frame(make_ohlcv(rows=120, seed=1))

        self.assertTrue(frame["score"].iloc[:40].isna().all())
        self.assertTrue(frame["score"].iloc[-1] >= 0)




class HistoryLengthTest(unittest.TestCase):
    """/analyze scores 2 years of history, the daily record 5: the last row must not depend on it."""

    def test_two_and_five_years_give_the_same_view(self):
        import pandas as pd

        for seed in range(20):
            with self.subTest(seed=seed):
                df = make_ohlcv(rows=1260, seed=seed)
                two_years = df[df.index > df.index[-1] - pd.Timedelta(days=731)]
                full, short = score_frame(df).iloc[-1], score_frame(two_years).iloc[-1]
                for column in ("ema20", "ema50", "rsi", "macd", "volatility", "score", "signal"):
                    self.assertEqual(full[column], short[column], column)
