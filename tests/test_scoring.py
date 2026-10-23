import unittest

from core.analytics.scoring import calculate_score


def score(**overrides):
    base = dict(ma20=10, ma50=9, rsi=50, macd=1, volume_ratio=1.0, volatility=0.04)
    base.update(overrides)
    return calculate_score(**base)


class ScoringTest(unittest.TestCase):
    def test_score_stays_in_range(self):
        best = score(rsi=25, volume_ratio=2, volatility=0.01)
        worst = score(ma20=8, rsi=90, macd=-1, volume_ratio=0.5, volatility=0.1)

        self.assertEqual(best["score"], 100)
        self.assertEqual(worst["score"], 0)

    def test_bullish_inputs_give_buy_side_signal(self):
        result = score()

        self.assertEqual(result["score"], 90)
        self.assertEqual(result["signal"], "STRONG BUY")

    def test_bearish_inputs_give_sell_side_signal(self):
        result = score(ma20=8, macd=-1)

        self.assertEqual(result["score"], 10)
        self.assertEqual(result["signal"], "STRONG SELL")

    def test_factors_explain_the_score(self):
        result = score()

        self.assertEqual(sum(result["factors"].values()) + 50, result["score"])
