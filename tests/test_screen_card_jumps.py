"""
Öz-denetim 6 / EVRE 0, bulgu D1: the /tara history card must leave out the stocks the research
leaves out (an unresolved ±20% jump, i.e. an unadjusted bonus/rights issue or split, or fewer
than 300 candles: core.backtest.run.tradable_symbols). Before v0.87.0 the card read every past
member, so a −60% data jump counted as a −60% trade in the cards and template cards.
"""

import unittest
from unittest import mock

import pandas as pd

from core.screen import command
from tests.test_screen import walk


class HistoryDataTest(unittest.TestCase):
    def setUp(self):
        command._HISTORY.clear()
        self.addCleanup(command._HISTORY.clear)

    def test_jumped_stocks_are_left_out(self):
        frames = {s: walk(400, 0.0, i) for i, s in enumerate(("A.IS", "B.IS", "FENER.IS"))}
        bench = walk(400, 0.0, 9)
        asked = {}

        def load(symbols, include_holdout=False):
            asked.setdefault("symbols", list(symbols))
            return {s: frames[s] for s in symbols} if "XU100.IS" not in symbols else {"XU100.IS": bench}

        with mock.patch("core.market.membership.ever_members", return_value=list(frames)), \
                mock.patch("core.backtest.run.tradable_symbols", return_value=(["A.IS", "B.IS"], ["FENER.IS"])), \
                mock.patch("core.backtest.run.load_frames", side_effect=load), \
                mock.patch("core.market.membership.membership_panel",
                           side_effect=lambda index, symbols: pd.DataFrame(True, index=index, columns=symbols)):
            got, _, eligible = command._history_data()
        self.assertEqual(sorted(got), ["A.IS", "B.IS"])
        self.assertNotIn("FENER.IS", eligible.columns)
        self.assertEqual(command.history_skipped(), ["FENER.IS"])


if __name__ == "__main__":
    unittest.main()
