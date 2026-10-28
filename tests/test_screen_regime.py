"""
Talimat C §C2.5: `rejim=` is a filter only. The live list runs when today's regime is the chosen
one and says so when it is not; the card counts only the days whose own regime was the chosen
one (each day's label uses data up to that day, K-51).
"""

import unittest
from unittest import mock

import numpy as np
import pandas as pd

from core.screen import card, engine
from core.screen.language import ScreenError, parse
from tests.test_screen_card import flat


class LanguageTest(unittest.TestCase):
    def test_option(self):
        q = parse("rsi<30 rejim=dusus")
        self.assertEqual(q.regime, "dusus")
        self.assertIn("rejim=dusus", q.text)  # part of the criterion: a different card
        self.assertEqual(parse("rsi<30 rejim=yüksek_oynaklık").regime, "yuksek_oynaklik")
        self.assertEqual(parse("rsi<30").regime, "")
        self.assertNotIn("rejim", parse("rsi<30").text)

    def test_unknown_value(self):
        with self.assertRaises(ScreenError) as caught:
            parse("rsi<30 rejim=boga")
        self.assertIn("yukselis", str(caught.exception))


def labels_for(index, chosen_days, label="düşüş", other="yükseliş"):
    out = pd.Series(other, index=index, dtype=object)
    out.loc[chosen_days] = label
    return out


class LiveTest(unittest.TestCase):
    def setUp(self):
        stock, bench = flat(), flat()
        stock.loc[stock.index[-1], "close"] = 101.0
        self.frames, self.bench = {"A.IS": stock}, bench

    def run_with(self, today):
        q = parse("kapanis>100,5 rejim=dusus ele=hayir")
        with mock.patch("core.market.regime.labels", return_value=labels_for(self.bench.index, [], other=today)):
            return engine.run(q, self.frames, self.bench, actions=[])

    def test_list_runs_in_the_chosen_regime(self):
        result = self.run_with("düşüş")
        self.assertEqual([m.symbol for m in result.matches], ["A.IS"])
        self.assertEqual(result.regime, "düşüş")

    def test_a_stock_without_prices_does_not_break_the_regime(self):
        # öz-denetim 8: the live list passes None / empty frames for stocks without data
        frames = {**self.frames, "B.IS": None, "C.IS": pd.DataFrame()}
        result = engine.run(parse("kapanis>100,5 rejim=dusus ele=hayir"), frames, self.bench, actions=[])
        self.assertEqual(result.regime, "bilinmiyor")  # one stock: no breadth
        self.assertTrue(result.regime_blocked)

    def test_a_small_universe_takes_todays_bist100_label(self):
        q = parse("kapanis>100,5 rejim=dusus ele=hayir evren=izleme")
        with mock.patch("core.market.regime.today_label", return_value="düşüş") as today:
            result = engine.run(q, self.frames, self.bench, actions=[])
        today.assert_called_once()
        self.assertEqual([m.symbol for m in result.matches], ["A.IS"])

    def test_list_is_empty_and_says_why_otherwise(self):
        from core.screen.command import format_result

        result = self.run_with("yükseliş")
        self.assertEqual(result.matches, [])
        self.assertTrue(result.regime_blocked)
        text = format_result(result, None)
        self.assertIn("Bugünkü rejim: yükseliş", text)
        self.assertIn("rejim=dusus", text)


class CardTest(unittest.TestCase):
    def test_only_days_of_the_chosen_regime_count(self):
        stock, bench = flat(), flat()
        days = stock.index[[100, 120, 140, 160]]
        stock.loc[days, "close"] = 101.0  # the condition holds on four separate days
        chosen = stock.index[[120, 160]]
        with mock.patch("core.market.regime.labels", return_value=labels_for(bench.index, chosen)):
            stats = card.history(parse("kapanis>100,5 rejim=dusus ele=hayir"), {"A.IS": stock}, bench,
                                 horizons=(5,))[5]
        self.assertEqual(stats.n, 2)
        plain = card.history(parse("kapanis>100,5 ele=hayir"), {"A.IS": stock}, bench, horizons=(5,))[5]
        self.assertEqual(plain.n, 4)

    def test_labels_get_the_card_data(self):
        stock, bench = flat(), flat()
        seen = {}

        def fake(close, frames, eligible):
            seen["n"] = len(close)
            seen["frames"] = sorted(frames)
            return pd.Series("bilinmiyor", index=close.index, dtype=object)

        with mock.patch("core.market.regime.labels", side_effect=fake):
            stats = card.history(parse("kapanis>99 rejim=yukselis ele=hayir"), {"A.IS": stock}, bench,
                                 horizons=(5,))[5]
        self.assertEqual(stats.n, 0)  # no day was "yükseliş"
        self.assertEqual(seen["frames"], ["A.IS"])
        self.assertTrue(np.isfinite(seen["n"]))


if __name__ == "__main__":
    unittest.main()
