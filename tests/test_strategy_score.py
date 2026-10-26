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


