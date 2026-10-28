"""
PC findings on real data (28.10.2026, /tara v0.75.0): the list said "BIST 100" but scanned the
118-stock QuantBIST list (ADESE left BIST 100 on 2022-04-01); ANELE showed ATR 45% from one
out-of-limit day. The default universe is now today's official membership (the card's own
source), and an ATR built on an out-of-limit move says so.
"""

import unittest
from datetime import date
from unittest import mock

import numpy as np

from core.screen import command, engine, universe
from core.screen.language import parse
from tests.test_screen import market


class UniverseTest(unittest.TestCase):
    def test_bist100_is_todays_membership(self):
        symbols = universe.symbols("bist100", today=date(2026, 10, 28))
        self.assertEqual(len(symbols), 100)
        self.assertNotIn("ADESE.IS", symbols)  # left BIST 100 on 2022-04-01
        self.assertIn("HALKB.IS", symbols)  # a member missing from data/universe.csv

    def test_the_quantbist_list_is_its_own_option(self):
        from core.market.universe import load_universe

        self.assertEqual(universe.symbols("quantbist"), load_universe())
        self.assertEqual(parse("rsi<30 evren=quantbist").text, "rsi<30 evren=quantbist")

    def test_label_names_the_list_and_its_size(self):
        frames, bench = market()
        result = engine.run(parse("rsi>0 evren=quantbist"), frames, bench)
        self.assertIn("QuantBIST evreni", command.format_result(result, None))
        result = engine.run(parse("rsi>0"), frames, bench)
        self.assertIn("BIST 100 (güncel üyelik)", command.format_result(result, None))

    def test_daily_update_covers_todays_bist100(self):
        from core.reports import daily

        with mock.patch.object(daily, "load_universe", return_value=["THYAO.IS"]), \
                mock.patch("core.market.membership.members_on", return_value={"HALKB", "THYAO"}):
            symbols = daily.symbols_to_update(daily.Paths(), universe=["THYAO.IS"])
        self.assertIn("HALKB.IS", symbols)


class AtrSpikeTest(unittest.TestCase):
    def test_an_out_of_limit_move_is_flagged(self):
        frames, bench = market()
        df = frames["S05.IS"].copy()
        df.iloc[-4, df.columns.get_loc("close")] *= 0.6  # one day -40%: no BIST session allows it
        df.iloc[-4, df.columns.get_loc("low")] = df.iloc[-4]["close"]
        frames["S05.IS"] = df
        result = engine.run(parse("rsi>-1 ele=hayir"), frames, bench)
        flagged = {m.symbol: m.flags for m in result.matches}
        self.assertTrue(any("uç hareket" in f for f in flagged["S05.IS"]))
        self.assertEqual(flagged["S06.IS"], [])
        self.assertIn("⚠️ ATR son 14 seansta ±%10 limitini aşan bir hareket içeriyor",
                      command.format_result(result, None))
        self.assertIn("düzeltilmemiş sıçrama", dict(engine.run(parse("rsi>-1"), frames, bench).eliminated)["S05.IS"])


    def test_a_limit_down_streak_like_anele(self):
        """ANELE 19-27.10.2026: five limit-down days then two limit-up days, all confirmed by the
        second source (datacheck 28.10 12:25). No single move breaks the limit, but the ATR was
        built at a much higher price."""
        frames, bench = market()
        df = frames["S07.IS"].copy()
        steps = np.array([0.9] * 5 + [1.1] * 2)
        prices = df["close"].iloc[-8] * np.cumprod(steps)
        for i, p in enumerate(prices):
            row = len(df) - 7 + i
            df.iloc[row, df.columns.get_indexer(["open", "high", "low", "close"])] = [p, p * 1.01, p * 0.99, p]
        frames["S07.IS"] = df
        result = engine.run(parse("rsi>-1 ele=hayir"), frames, bench)
        flags = {m.symbol: m.flags for m in result.matches}["S07.IS"]
        self.assertFalse(any("limitini aşan" in f for f in flags))
        self.assertTrue(any("sert hareket" in f for f in flags))
        # since K-45 such a stock is eliminated by default (7 limit days in 10 sessions)
        self.assertIn("tavan/taban", dict(engine.run(parse("rsi>-1"), frames, bench).eliminated)["S07.IS"])


if __name__ == "__main__":
    unittest.main()
