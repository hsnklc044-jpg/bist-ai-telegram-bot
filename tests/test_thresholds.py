import unittest

from core.config.thresholds import LOWEST_ACTION, action_for_score


class ActionLadderTest(unittest.TestCase):
    def test_boundaries(self):
        cases = {
            100: "STRONG BUY",
            90: "STRONG BUY",
            89.9: "BUY",
            75: "BUY",
            60: "ACCUMULATE",
            45: "HOLD",
            30: "REDUCE",
            15: "SELL",
            14.9: LOWEST_ACTION,
            0: LOWEST_ACTION,
        }

        for score, action in cases.items():
            with self.subTest(score=score):
                self.assertEqual(action_for_score(score), action)

    def test_committee_uses_same_ladder(self):
        from core.committee.engine import _score_to_vote
        from core.decision.builder import _action

        for score in range(0, 101, 5):
            with self.subTest(score=score):
                self.assertEqual(_score_to_vote(score).value, _action(score))
