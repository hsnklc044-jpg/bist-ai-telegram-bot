"""
/tara engine (core/screen/, Aşama 1): the field library on the live analysis' own calculation
path, the expression language (own parser, no eval), the universe with its liquidity floor and
named eliminations, the closed-candle rule, and the speed of a full BIST 100 scan.
"""

import time
import unittest
from datetime import datetime

import numpy as np
import pandas as pd

from core.market.calendar import ISTANBUL
from core.screen import engine, fields, language
from core.screen.language import ScreenError, parse
from core.strategy.score import score_frame


def bars(close, volume=2e6, start="2025-01-02", seed=0):
    rng = np.random.default_rng(seed)
    close = pd.Series(np.asarray(close, dtype=float))
    index = pd.bdate_range(start, periods=len(close))
    close.index = index
    spread = np.abs(rng.normal(0, 0.006, len(close)))
    return pd.DataFrame({"open": close.shift(1).fillna(close.iloc[0]) * (1 + rng.normal(0, 0.002, len(close))),
                         "high": close * (1 + spread), "low": close * (1 - spread), "close": close,
                         "volume": volume * (1 + np.abs(rng.normal(0, 0.3, len(close))))}, index=index)


def walk(n=320, drift=0.0005, seed=1, start=100.0, volume=2e6):
    rng = np.random.default_rng(seed)
    return bars(start * np.exp(np.cumsum(rng.normal(drift, 0.015, n))), volume=volume, seed=seed)


# --- language -------------------------------------------------------------------------------------


class ParserTest(unittest.TestCase):
    def test_comparisons_ranges_events_and_logic(self):
        cases = {
            "rsi<35": "rsi<35",
            "RSI < 35 ve ema20>ema50": "rsi<35 ve ema20>ema50",
            "rsi 30..50": "rsi 30..50",
            "rsi(7)>70": "rsi(7)>70",
            "ema(100)<kapanis": "ema(100)<kapanis",
            "sma200<kapanis": "sma(200)<kapanis",
            "kesti_yukari(ema20,ema50)": "kesti_yukari(ema20,ema50)",
            "son(5, kesti_asagi(macd, macd_sinyal))": "son(5,kesti_asagi(macd,macd_sinyal))",
            "rsi<30 VEYA (hacim_oran>2 VE DEĞİL macd>0)": "(rsi<30 veya (hacim_oran>2 ve degil macd>0))",
            "hacim_oran>1,5": "hacim_oran>1.5",
            "getiri_20g>-5": "getiri_20g>-5",
            "rsi<=30": "rsi<=30",
        }
        for text, canonical in cases.items():
            with self.subTest(text=text):
                self.assertEqual(parse(text).text, canonical)

    def test_options(self):
        q = parse("rsi<30 evren=izleme likidite=0 sirala=rsi")
        self.assertEqual((q.universe, q.liquidity, q.order), ("izleme", 0.0, "rsi"))
        default = parse("rsi<30")
        self.assertEqual((default.universe, default.liquidity, default.order), ("bist100", 10.0, "alfabetik"))
        self.assertEqual(parse("rsi<30 likidite=25").text, "rsi<30 likidite=25")  # non-default options are part of the criterion
        self.assertEqual(parse("rsi<30 sirala=hacim").text, "rsi<30")  # order is not
        self.assertEqual(parse("rsi<30 sıra:güç").order, "goreli_guc")  # v0.75.0 spelling

    def test_errors_point_at_the_place_and_suggest(self):
        cases = {
            "rsx<30": ("'rsx' bilinmeyen alan", "'rsi' mi demek istediniz?", 0),
            "rsi<30 ve emma20>ema50": ("'emma20' bilinmeyen alan", "'ema20' mi", 10),
            "rsi=30": ("< ya da > kullanın", "", 3),
            "rsi<": ("eksik", "", 4),
            "(rsi<30": ("kapanmamış parantez", "", 7),
            "rsi<30)": ("fazladan ')'", "", 6),
            "30<40": ("en az bir alan", "", 0),
            "rsi(1)<30": ("2 ile 250 arasında", "", 4),
            "rsi<30; rm -rf /": ("izin verilmeyen karakter ';'", "", 6),
            "__import__('os')": ("izin verilmeyen karakter", "", 11),
            "evren=bist500 rsi<30": ("evren", "bist100", 6),
            "kesti_yukari(ema20)": ("iki değer", "", 18),
            "son(0, rsi<30)": ("1 ile 60 arasında", "", 4),
            "rsi 50..30": ("küçük sayı önce", "", 4),
        }
        for text, (message, hint, column) in cases.items():
            with self.subTest(text=text), self.assertRaises(ScreenError) as caught:
                parse(text)
            shown = str(caught.exception)
            self.assertIn(message, shown)
            self.assertIn(hint, shown)
            self.assertIn(language.normalize(text) + "\n" + " " * column + "^", shown)
            self.assertIn("Örnek: /tara", shown)

    def test_limits(self):
        with self.assertRaises(ScreenError) as caught:
            parse("rsi<30 " * 16)
        self.assertIn("en fazla 15 koşul", str(caught.exception))
        with self.assertRaises(ScreenError) as caught:
            parse("rsi<30 ve " + "x" * 300)
        self.assertIn("en fazla 300 karakter", str(caught.exception))
        parse(" ve ".join(["rsi<30"] * 15))  # exactly fifteen is fine

    def test_no_eval_anywhere(self):
        import inspect

        from core.screen import language as module

        source = inspect.getsource(module)
        for word in ("eval(", "exec(", "compile(", "__import__"):
            self.assertNotIn(word, source.replace('"__import__', ""))


# --- fields ---------------------------------------------------------------------------------------


class FieldTest(unittest.TestCase):
    def setUp(self):
        self.df, self.bench = walk(320, seed=3), walk(320, 0.0, seed=4)

    def table(self, *names):
        return fields.table(self.df, self.bench["close"], sorted({f for n in names for f in parse(n).fields}))

    def test_same_values_as_the_live_analysis(self):
        sf = score_frame(self.df)
        t = self.table("ema20>0", "ema50>0", "rsi>0", "macd>0", "hacim_oran>0", "atr_yuzde>0")
        pd.testing.assert_series_equal(t["ema20"], sf["ema20"], check_names=False)
        pd.testing.assert_series_equal(t["ema50"], sf["ema50"], check_names=False)
        pd.testing.assert_series_equal(t["rsi"], sf["rsi"], check_names=False)
        pd.testing.assert_series_equal(t["macd"], sf["macd"], check_names=False)
        pd.testing.assert_series_equal(t["hacim_oran"], sf["volume_ratio"], check_names=False)
        pd.testing.assert_series_equal(t["atr_yuzde"], sf["volatility"] * 100, check_names=False)

    def test_every_field_computes(self):
        names = [f"{name}>-1000000" for name in fields.FIELDS if name not in fields.CROSS_SECTIONAL] + ["ema(30)>0", "sma(10)>0", "rsi(7)>0",
                                                                    "roc(5)>-100", "atr(20)>0", "adx(20)>0"]
        t = fields.table(self.df, self.bench["close"], sorted({f for n in names for f in parse(n).fields}))
        last = t.iloc[-1]
        for column in t.columns:
            with self.subTest(column=column):
                self.assertFalse(pd.isna(last[column]), column)

    def test_definitions(self):
        t = self.table("getiri_60g>0", "gg_20>0", "zirve_uzaklik>-100", "yuksek_20g>0", "bosluk>-100",
                       "islem_tl>0", "uzaklik_ema(50)>-100", "supertrend>-2", "bb_yuzde>-100")
        c, last = self.df["close"], t.iloc[-1]
        self.assertAlmostEqual(last["getiri_60g"], (c.iloc[-1] / c.iloc[-61] - 1) * 100)
        b = self.bench["close"]
        self.assertAlmostEqual(last["gg_20"], (c.iloc[-1] / c.iloc[-21] - 1) * 100 - (b.iloc[-1] / b.iloc[-21] - 1) * 100)
        self.assertAlmostEqual(last["zirve_uzaklik"], (c.iloc[-1] / c.iloc[-252:].max() - 1) * 100)
        self.assertAlmostEqual(last["yuksek_20g"], self.df["high"].iloc[-21:-1].max())  # today excluded
        self.assertAlmostEqual(last["bosluk"], (self.df["open"].iloc[-1] / c.iloc[-2] - 1) * 100)
        self.assertAlmostEqual(last["islem_tl"], (c * self.df["volume"]).iloc[-20:].mean() / 1e6)
        ema50 = score_frame(self.df)["ema50"].iloc[-1]
        self.assertAlmostEqual(last["uzaklik_ema(50)"], (c.iloc[-1] / ema50 - 1) * 100)
        self.assertIn(last["supertrend"], (1.0, -1.0))
        self.assertTrue(-100 < last["bb_yuzde"] < 200)

    def test_breakout_on_the_previous_20_days_can_happen(self):
        rising = bars(np.linspace(100, 160, 120), seed=5)
        t = fields.table(rising, rising["close"], ["kapanis", "yuksek_20g"])
        self.assertTrue((t["kapanis"] > t["yuksek_20g"]).iloc[-10:].any())


class EvaluationTest(unittest.TestCase):
    def test_events_and_window(self):
        index = pd.bdate_range("2026-01-01", periods=6)
        t = pd.DataFrame({"ema20": [1, 1, 3, 3, 1, 1], "ema50": [2, 2, 2, 2, 2, 2]}, index=index, dtype=float)
        self.assertEqual(list(parse("kesti_yukari(ema20,ema50)").mask(t)), [False, False, True, False, False, False])
        self.assertEqual(list(parse("kesti_asagi(ema20,ema50)").mask(t)), [False, False, False, False, True, False])
        self.assertEqual(list(parse("son(2, kesti_yukari(ema20,ema50))").mask(t)), [False, False, True, True, False, False])
        self.assertEqual(list(parse("degil ema20>ema50").mask(t)), [True, True, False, False, True, True])
        self.assertEqual(list(parse("ema20 1..2").mask(t)), [True, True, False, False, True, True])

    def test_missing_values_never_match(self):
        t = pd.DataFrame({"rsi": [np.nan, 20.0]}, index=pd.bdate_range("2026-01-01", periods=2))
        self.assertEqual(list(parse("rsi<30").mask(t)), [False, True])
        self.assertEqual(list(parse("degil rsi>30").mask(t)), [False, True])  # NaN is not "not above"


class FastAtrTest(unittest.TestCase):
    def test_bit_for_bit_the_same_as_ta(self):
        from ta.volatility import AverageTrueRange

        from core.strategy.score import average_true_range

        for n, seed in ((14, 1), (10, 2), (14, 3)):
            df = walk(400, 0.0, seed)
            df.iloc[5, df.columns.get_loc("high")] = np.nan  # a gap in the data too
            ours = average_true_range(df["high"], df["low"], df["close"], window=n)
            theirs = AverageTrueRange(df["high"], df["low"], df["close"], window=n).average_true_range()
            np.testing.assert_array_equal(ours.to_numpy(), theirs.to_numpy())
        short = walk(5, 0.0, 4)
        self.assertTrue((average_true_range(short["high"], short["low"], short["close"]) == 0).all())


class FastAdxTest(unittest.TestCase):
    def test_bit_for_bit_the_same_as_ta(self):
        from ta.trend import ADXIndicator

        for n, seed in ((14, 1), (20, 2), (7, 3)):
            df = walk(500, 0.0004, seed)
            ours = fields._adx(df["high"], df["low"], df["close"], n)
            theirs = ADXIndicator(df["high"], df["low"], df["close"], window=n).adx()
            np.testing.assert_array_equal(ours.to_numpy(), theirs.to_numpy())
        short = walk(20, 0.0, 4)
        self.assertTrue(fields._adx(short["high"], short["low"], short["close"], 14).isna().all())


# --- universe and live run ------------------------------------------------------------------------


def market(n=40):
    frames = {f"S{i:02d}.IS": walk(320, 0.0005, 10 + i, volume=2e6) for i in range(n)}
    frames["THIN.IS"] = walk(320, 0.0005, 99, volume=1e3)  # ~0.1 mn TL a day
    return frames, walk(320, 0.0, 7)


class LiveTest(unittest.TestCase):
    def test_liquidity_floor_and_named_eliminations(self):
        frames, bench = market()
        frames["OLD.IS"] = frames["S00.IS"].iloc[:-2]  # last close is not the last session
        result = engine.run(parse("rsi>0"), frames, bench, suspects={"S01"})
        symbols = [m.symbol for m in result.matches]
        self.assertNotIn("THIN.IS", symbols)
        self.assertEqual(result.illiquid, ["THIN.IS"])
        self.assertEqual(dict(result.missing), {"OLD.IS": "son kapanış " + f"{frames['OLD.IS'].index[-1]:%d.%m}",
                                                "S01.IS": "ikinci kaynakta fark (düzeltme bekliyor)"})
        self.assertIn("THIN.IS", [m.symbol for m in engine.run(parse("rsi>0 likidite=0"), frames, bench).matches])

    def test_orders(self):
        frames, bench = market()
        by_rsi = engine.run(parse("rsi>0 sirala=rsi"), frames, bench).matches
        self.assertEqual([m.values["rsi"] for m in by_rsi], sorted(m.values["rsi"] for m in by_rsi))
        by_strength = engine.run(parse("rsi>0 sirala=goreli_guc"), frames, bench).matches
        self.assertEqual([m.values["gg_20"] for m in by_strength],
                         sorted((m.values["gg_20"] for m in by_strength), reverse=True))
        alphabetical = engine.run(parse("rsi>0"), frames, bench).matches
        self.assertEqual([m.symbol for m in alphabetical], sorted(m.symbol for m in alphabetical))

    def test_percentile_rank_inside_the_scanned_universe(self):
        frames, bench = market()
        result = engine.run(parse("gg_sira>80 likidite=0"), frames, bench)
        everyone = engine.run(parse("gg_sira>-1 likidite=0"), frames, bench).matches
        top = sorted(everyone, key=lambda m: m.values["gg_60"])[-len(result.matches):]
        self.assertEqual(sorted(m.symbol for m in result.matches), sorted(m.symbol for m in top))
        self.assertTrue(all(0 <= m.values["gg_sira"] <= 100 for m in everyone))

    def test_closed_candle_rule_note(self):
        from datetime import date

        day = date(2026, 10, 27)
        note = engine.time_note(day, datetime(2026, 10, 28, 11, 0, tzinfo=ISTANBUL))  # during the session
        self.assertIn("27.10.2026 kapanışına göre", note)
        self.assertIn("henüz kapanmadı", note)
        self.assertEqual(engine.time_note(day, datetime(2026, 10, 27, 20, 0, tzinfo=ISTANBUL)), "")

    def test_full_bist100_scan_is_fast(self):
        frames = {f"S{i:02d}.IS": walk(1250, 0.0003, 200 + i) for i in range(100)}  # five years, as on the PC
        bench = walk(1250, 0.0, 8)
        import sys

        query = parse("ema20>ema50 ve rsi 30..70 ve son(5, kesti_yukari(macd,macd_sinyal)) ve gg_sira>50 "
                      "ve supertrend>0 ve adx>20 ve bb_genislik_yuzdelik<50")
        tracer = sys.gettrace()  # coverage traces every line (~2x slower): measure the code, not the tracer
        sys.settrace(None)
        try:
            started = time.perf_counter()
            engine.run(query, frames, bench)
            elapsed = time.perf_counter() - started
        finally:
            sys.settrace(tracer)
        self.assertLess(elapsed, 5.0)


class UniverseTest(unittest.TestCase):
    def test_lists_and_their_errors(self):
        import tempfile
        from pathlib import Path
        from unittest import mock

        from core.screen import universe

        self.assertTrue(len(universe.symbols("bist100")) >= 90)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ScreenError) as caught:
                universe.symbols("bist30", bist30_path=Path(tmp) / "bist30.csv")
            self.assertIn("BIST 30 listesi henüz sistemde yok", str(caught.exception))
            (Path(tmp) / "bist30.csv").write_text("symbol,source\nthyao,x\nAKBNK.IS,x\n", encoding="utf-8")
            self.assertEqual(universe.symbols("bist30", bist30_path=Path(tmp) / "bist30.csv"), ["THYAO.IS", "AKBNK.IS"])
        with mock.patch("core.watchlist.service.get_watchlist", return_value=["eregl", "THYAO.IS"]):
            self.assertEqual(universe.symbols("izleme", chat_id=1), ["EREGL.IS", "THYAO.IS"])
        with mock.patch("core.watchlist.service.get_watchlist", return_value=[]), self.assertRaises(ScreenError):
            universe.symbols("izleme", chat_id=1)

    def test_suspects_are_read_at_most_hourly(self):
        from core.screen import universe

        universe._suspects.clear()
        calls = []

        def fetch():
            calls.append(1)
            return {"differing": ["SKBNK"]}

        self.assertEqual(universe.suspects(fetch, now=1000.0), {"SKBNK"})
        self.assertEqual(universe.suspects(fetch, now=2000.0), {"SKBNK"})
        self.assertEqual(len(calls), 1)
        self.assertEqual(universe.suspects(lambda: None, now=1000.0 + universe.SUSPECTS_TTL), set())
        universe._suspects.clear()


class HandbookTest(unittest.TestCase):
    def test_every_field_is_documented(self):
        from pathlib import Path

        text = (Path(__file__).resolve().parents[1] / "docs" / "HANDBOOK.md").read_text(encoding="utf-8")
        section = text[text.index("## 8. Gösterge taraması (/tara)"):]
        for name in fields.FIELDS:
            self.assertIn(f"`{name}", section, name)


if __name__ == "__main__":
    unittest.main()
