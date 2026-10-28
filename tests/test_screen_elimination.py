"""
Profesyonel filtreler, Aşama 1 (DECISIONS K-45): elimination filters on every /tara result by
default, each one can be turned off. Liquidity (previous 20 full sessions < 15 mn TL), a recent
corporate action (rights issue, bonus/split, IPO in the last 60 sessions; no record = unknown, not
eliminated), extreme moves (3+ limit days in 10 sessions, or ATR% in the top 5% of the scanned
list) and data problems (unresolved ±20% jump in 252 sessions, 3+ zero-volume days in 20, second
source difference). Each eliminated stock is named with its reason; the card applies the same
filters with each day's own data.
"""

import unittest

import numpy as np

from core.market.corrections import CorporateAction
from core.screen import command, elimination, engine
from core.screen.language import ScreenError, parse
from tests.test_screen_engine import walk


def stock(n=400, seed=1, volume=3e6, price=100.0):
    return walk(n, 0.0, seed, start=price, volume=volume)


class OptionsTest(unittest.TestCase):
    def test_default_and_switches(self):
        q = parse("rsi>0")
        self.assertEqual(q.elimination, elimination.Settings())
        self.assertEqual(q.liquidity, 15.0)
        self.assertEqual(parse("rsi>0 ele=hayir").elimination, elimination.Settings.off())
        self.assertEqual(parse("rsi>0 ele_likidite=0").elimination.liquidity, 0.0)
        self.assertEqual(parse("rsi>0 likidite=5").elimination.liquidity, 5.0)  # the older name still works
        self.assertFalse(parse("rsi>0 ele_kurumsal=0").elimination.corporate)
        self.assertFalse(parse("rsi>0 ele_hareket=hayir").elimination.move)
        self.assertFalse(parse("rsi>0 ele_veri=0").elimination.data)

    def test_canonical_text(self):
        self.assertEqual(parse("rsi>0").text, "rsi>0")
        self.assertEqual(parse("rsi>0 ele=hayir").text, "rsi>0 ele=hayir")
        self.assertEqual(parse("rsi>0 ele_kurumsal=0 likidite=5").text, "rsi>0 likidite=5 ele_kurumsal=0")
        self.assertEqual(parse(parse("rsi>0 ele_veri=0").text).elimination, parse("rsi>0 ele_veri=0").elimination)

    def test_bad_values(self):
        for text in ("rsi>0 ele=belki", "rsi>0 ele_hareket=2", "rsi>0 ele_likidite=-1"):
            with self.subTest(text=text), self.assertRaises(ScreenError):
                parse(text)


class ReasonTest(unittest.TestCase):
    def reasons(self, df, actions=(), bench=None, settings=None):
        bench = bench if bench is not None else stock(len(df), 99)
        frame = elimination.frame(df, "X.IS", bench.index, list(actions))
        return elimination.reasons(frame.iloc[-1], settings or elimination.Settings())

    def test_liquidity_uses_the_previous_twenty_sessions(self):
        thin = stock(volume=50_000)  # 100 TL × 50 000 = 5 mn TL
        self.assertRegex(self.reasons(thin)[0], r"^likidite \d+ mn TL")
        today_only = stock(volume=50_000)
        today_only.iloc[-1, today_only.columns.get_loc("volume")] = 1e9  # today's session is not counted
        self.assertTrue(self.reasons(today_only)[0].startswith("likidite"))
        self.assertEqual(self.reasons(stock()), [])

    def test_corporate_action_in_sixty_sessions(self):
        df = stock()
        recent = CorporateAction("X.IS", df.index[-20].date(), kind="rights", ratio=1.0, price=1.0)
        self.assertEqual(self.reasons(df, [recent]), [f"bedelli {df.index[-20]:%d.%m}"])
        old = CorporateAction("X.IS", df.index[-70].date(), kind="rights", ratio=1.0, price=1.0)
        self.assertEqual(self.reasons(df, [old]), [])
        bonus = CorporateAction("X.IS", df.index[-5].date(), kind="bonus", ratio=1.0)
        self.assertEqual(self.reasons(df, [bonus]), [f"bedelsiz/bölünme {df.index[-5]:%d.%m}"])
        other = CorporateAction("Y.IS", df.index[-5].date(), kind="rights", ratio=1.0)
        self.assertEqual(self.reasons(df, [other]), [])
        fix = CorporateAction("X.IS", df.index[-5].date(), factor=0.5)  # a data fix, not an action
        self.assertEqual(self.reasons(df, [fix]), [])

    def test_ipo(self):
        bench = stock(400, 99)
        listed = stock(40, 3)
        listed.index = bench.index[-40:]
        self.assertEqual(self.reasons(listed, bench=bench), [f"halka arz {listed.index[0]:%d.%m}"])
        self.assertEqual(self.reasons(stock(400, 3), bench=bench), [])  # traded since the data begins: not an IPO

    def test_limit_days(self):
        df = stock()
        close = df["close"].to_numpy().copy()
        for i in (-9, -6, -2):
            close[i:] *= 1.13
        df["close"] = close
        self.assertIn("10 seansta 3 tavan/taban", self.reasons(df))

    def test_data_problems(self):
        jumped = stock()
        jumped.iloc[-100:, :4] *= 0.4  # an unadjusted rights issue
        self.assertEqual(self.reasons(jumped), [f"veri: düzeltilmemiş sıçrama {jumped.index[-100]:%d.%m}"])
        quiet = stock()
        quiet.iloc[-8:-3, quiet.columns.get_loc("volume")] = 0
        self.assertIn("veri: 20 seansta 5 gün sıfır hacim", self.reasons(quiet))
        self.assertEqual(self.reasons(jumped, settings=elimination.Settings(data=False)), [])

    def test_no_record_means_unknown(self):
        self.assertIn("bilinmiyor", elimination.NOTE)


class EngineTest(unittest.TestCase):
    def market(self):
        frames = {f"S{i:02d}.IS": stock(400, 10 + i) for i in range(30)}
        frames["THIN.IS"] = stock(400, 50, volume=50_000)
        wild = stock(400, 51)
        wild[["high", "low"]] = wild[["close"]].to_numpy() * np.array([1.12, 0.88])
        frames["WILD.IS"] = wild
        return frames, stock(400, 99)

    def test_named_with_the_reason_and_switchable(self):
        frames, bench = self.market()
        result = engine.run(parse("rsi>0"), frames, bench, actions=[])
        reasons = dict(result.eliminated)
        self.assertTrue(reasons["THIN.IS"].startswith("likidite"))
        self.assertIn("ATR %", reasons["WILD.IS"])
        self.assertNotIn("THIN.IS", {m.symbol for m in result.matches})
        text = command.format_result(result, None)
        self.assertIn("Elenen (", text)
        self.assertIn("THIN (likidite", text)
        self.assertIn("ele=hayir", text)
        free = engine.run(parse("rsi>0 ele=hayir"), frames, bench, actions=[])
        self.assertEqual(free.eliminated, [])
        self.assertIn("THIN.IS", {m.symbol for m in free.matches})

    def test_atr_rank_needs_a_real_list(self):
        frames, bench = self.market()
        small = {s: frames[s] for s in ("S00.IS", "S01.IS", "WILD.IS")}
        result = engine.run(parse("rsi>0"), small, bench, actions=[])
        self.assertNotIn("WILD.IS", dict(result.eliminated))  # top 5% of 3 stocks means nothing

    def test_second_source_difference_is_a_data_reason(self):
        frames, bench = self.market()
        result = engine.run(parse("rsi>0"), frames, bench, {"S00"}, actions=[])
        self.assertIn("ikinci kaynak", dict(result.eliminated)["S00.IS"])
        self.assertIn("S00.IS", {m.symbol for m in engine.run(parse("rsi>0 ele_veri=0"), frames, bench, {"S00"},
                                                            actions=[]).matches})


class ExplainTest(unittest.TestCase):
    def test_the_reason_is_shown_for_one_stock(self):
        frames = {"THIN.IS": stock(400, 50, volume=50_000), "S00.IS": stock(400, 10)}
        bench = stock(400, 99)
        text = command.explain_text(["THIN", "rsi>0"], live=lambda symbols: (frames, bench), suspects=set())
        self.assertIn("✗ eleme: likidite", text)
        self.assertIn("ele=hayir", text)
        ok = command.explain_text(["S00", "rsi>0"], live=lambda symbols: (frames, bench), suspects=set())
        self.assertIn("✓ elemelere takılmıyor", ok)
        flagged = command.explain_text(["S00", "rsi>0"], live=lambda symbols: (frames, bench), suspects={"S00"})
        self.assertIn("ikinci kaynakta fark", flagged)


class CardTest(unittest.TestCase):
    def test_same_filters_with_each_days_data(self):
        from core.screen import card
        from tests.test_screen import walk as walk_from_2023

        frames = {f"S{i:02d}.IS": walk_from_2023(1000, 0.0003, 60 + i, volume=3e6) for i in range(25)}
        bench = walk_from_2023(1000, 0.0, 77)
        thin = frames["S00.IS"]
        thin.iloc[:600, thin.columns.get_loc("volume")] = 10_000  # illiquid first, liquid later
        q = parse("rsi>0")
        base = card.history(q, frames, bench, actions=[])[5]
        free = card.history(parse("rsi>0 ele=hayir"), frames, bench, actions=[])[5]
        self.assertLess(base.n, free.n)
        later = {k: v.copy() for k, v in frames.items()}
        action = CorporateAction("S01.IS", later["S01.IS"].index[800].date(), kind="rights", ratio=1.0)
        after = card.history(q, later, bench, actions=[action])[5]
        self.assertLess(after.n, base.n)  # the 60 sessions from that day on are left out ...
        self.assertGreaterEqual(after.n, base.n - 61)  # ... and nothing before it (no look-ahead)

    def test_card_version_changes(self):
        from core.screen import card

        self.assertGreaterEqual(card.CARD_FORMAT, 4)


if __name__ == "__main__":
    unittest.main()
