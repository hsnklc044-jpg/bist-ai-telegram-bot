"""
/tara: a user-defined indicator filter over BIST 100 (a filter, not advice). The parser, the
live list, the history card (never past the holdout line, 30.10.2026), the live record and
the saved screens.
"""

import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from core.analytics import screen
from core.backtest.run import SCREEN_END
from core.market.calendar import ISTANBUL

NOW = datetime(2026, 10, 28, 20, 0, tzinfo=ISTANBUL)


def bars(close, volume=1e6, start="2023-01-02"):
    close = pd.Series(close, dtype=float)
    index = pd.bdate_range(start, periods=len(close))
    close.index = index
    return pd.DataFrame({"open": close * 0.999, "high": close * 1.01, "low": close * 0.99, "close": close,
                         "volume": volume}, index=index)


def walk(n, drift, seed, start=100.0, start_day="2023-01-02"):
    rng = np.random.default_rng(seed)
    return bars(start * np.exp(np.cumsum(rng.normal(drift, 0.01, n))), start=start_day)


class ParserTest(unittest.TestCase):
    def test_valid_expressions(self):
        s = screen.parse("RSI < 30 ve ema20>ema50")
        self.assertEqual([c.text for c in s.conditions], ["rsi<30", "ema20>ema50"])
        self.assertEqual(s.text, "rsi<30 ema20>ema50")
        self.assertEqual(screen.parse("hacim>1,5").conditions[0].right, 1.5)
        self.assertEqual(screen.parse("getiri_20g>-5").conditions[0].right, -5.0)
        self.assertEqual(screen.parse("göreli_güç>0").conditions[0].left, "goreli_guc")
        self.assertEqual(screen.parse("kapanış>ema50, macd>macd_sinyal").text, "kapanis>ema50 macd>macd_sinyal")
        self.assertEqual(screen.parse("rsi<40 sıra:güç").order, "guc")
        self.assertEqual(screen.parse("rsi<40").order, "alfabetik")

    def test_invalid_expressions_are_explained_in_turkish(self):
        cases = {
            "rsx<30": "Bilinmeyen alan 'rsx'",
            "rsi=30": "Karşılaştırma için < ya da > kullanın",
            "rsi<abc": "'abc' bir sayı ya da alan değil",
            "rsi<": "eksik",
            "rsi<30 rsi<31 rsi<32 rsi<33 rsi<34 rsi<35": "en fazla 5 koşul",
            "rsi<30 sıra:hacim": "Sıralama 'alfabetik' ya da 'güç'",
            "30<rsi": "solunda bir alan",
        }
        for text, message in cases.items():
            with self.subTest(text=text), self.assertRaises(screen.ScreenError) as caught:
                screen.parse(text)
            self.assertIn(message, str(caught.exception))
            self.assertIn("Örnek", str(caught.exception))


class IndicatorTest(unittest.TestCase):
    def test_fields(self):
        stock, bench = walk(300, 0.001, 1), walk(300, 0.0, 2)
        table = screen.indicators(stock, bench["close"])
        for name in screen.FIELDS:
            self.assertIn(name, table.columns)
        last = table.iloc[-1]
        self.assertAlmostEqual(last["getiri_5g"], (stock["close"].iloc[-1] / stock["close"].iloc[-6] - 1) * 100)
        bench_20 = bench["close"].iloc[-1] / bench["close"].iloc[-21] - 1
        self.assertAlmostEqual(last["goreli_guc"], last["getiri_20g"] - bench_20 * 100)
        self.assertAlmostEqual(last["atr_yuzde"], last["atr"] / stock["close"].iloc[-1] * 100)
        self.assertAlmostEqual(last["likidite"], (stock["close"] * stock["volume"]).iloc[-20:].mean())


def expected_low_rsi(frames, bench):
    return sorted(s for s, df in frames.items() if screen.indicators(df, bench["close"]).iloc[-1]["rsi"] < 30)


def market():
    """20 stocks; S00 and S01 fell hard in the last weeks (low RSI)."""
    frames = {}
    for i in range(20):
        df = walk(300, 0.0005, 10 + i)
        if i < 2:
            df.loc[df.index[-15:], ["open", "high", "low", "close"]] *= np.linspace(1, 0.7, 15)[:, None]
        frames[f"S{i:02d}.IS"] = df
    return frames, walk(300, 0.0, 99)


class LiveTest(unittest.TestCase):
    def test_matches_and_their_lines(self):
        frames, bench = market()
        matches = screen.run(screen.parse("rsi<30"), frames, bench)
        self.assertEqual([m.symbol for m in matches], expected_low_rsi(frames, bench))
        self.assertTrue({"S00.IS", "S01.IS"} <= {m.symbol for m in matches})  # the two that fell hard
        text = screen.format_result(screen.parse("rsi<30"), matches, None)
        self.assertIn("S00", text)
        self.assertIn("rsi", text)
        self.assertIn("1 ATR", text)
        self.assertIn("20g ort. işlem", text)
        self.assertTrue(text.rstrip().endswith(screen.DISCLAIMER))

    def test_order_by_relative_strength(self):
        frames, bench = market()
        matches = screen.run(screen.parse("rsi>0 sıra:güç"), frames, bench)
        strengths = [m.values["goreli_guc"] for m in matches]
        self.assertEqual(strengths, sorted(strengths, reverse=True))

    def test_a_stock_without_todays_candle_is_left_out(self):
        frames, bench = market()
        frames["S00.IS"] = frames["S00.IS"].iloc[:-3]
        self.assertNotIn("S00.IS", [m.symbol for m in screen.run(screen.parse("rsi<30"), frames, bench)])

    def test_words_and_length(self):
        frames, bench = market()
        many = screen.run(screen.parse("rsi>0 ema20>0 macd>-1000 hacim>0 atr_yuzde>0"), frames, bench) * 3
        card = {5: (0.001, 0.52, 1234), 20: (-0.002, 0.48, 1200)}
        text = screen.format_result(screen.parse("rsi>0 ema20>0 macd>-1000 hacim>0 atr_yuzde>0"), many, card)
        self.assertLessEqual(len(text), 4096)
        self.assertIn("(+45 hisse daha", text)
        import re

        body = text.replace(screen.DISCLAIMER, "").lower()
        for word in (r"\bal\b", r"\bsat\b", r"\balın\b", r"\bsatın\b", r"en iyi", r"öneri", r"tavsiye"):
            self.assertIsNone(re.search(word, body), word)


class HistoryCardTest(unittest.TestCase):
    def frames_across_the_holdout(self):
        frames = {f"S{i:02d}.IS": walk(1030, 0.0003, 50 + i, start_day="2023-01-02") for i in range(6)}
        return frames, walk(1030, 0.0, 77, start_day="2023-01-02")

    def test_never_uses_data_after_the_holdout_line(self):
        frames, bench = self.frames_across_the_holdout()
        self.assertGreater(frames["S00.IS"].index[-1], pd.Timestamp(SCREEN_END))  # data runs past it
        s = screen.parse("rsi>0")
        full = screen.history(s, frames, bench)
        cut = screen.history(s, {k: v.loc[:SCREEN_END] for k, v in frames.items()}, bench.loc[:SCREEN_END])
        self.assertEqual(full, cut)
        later = {k: v.copy() for k, v in frames.items()}  # change everything after the line: nothing moves
        for df in later.values():
            df.loc[df.index > pd.Timestamp(SCREEN_END), ["open", "close"]] *= 3
        self.assertEqual(screen.history(s, later, bench), full)

    def test_starts_at_the_screening_start_and_counts_samples(self):
        frames, bench = self.frames_across_the_holdout()
        card = screen.history(screen.parse("rsi>0"), frames, bench)
        mean, hit, n = card[5]
        self.assertGreater(n, 30)
        self.assertTrue(0 <= hit <= 1)
        early = {k: v.loc[:"2023-07-31"] for k, v in frames.items()}
        self.assertEqual(screen.history(screen.parse("rsi>0"), early, bench)[5][2], 0)

    def test_eligibility_and_small_samples(self):
        frames, bench = self.frames_across_the_holdout()
        nobody = pd.DataFrame(False, index=bench.index, columns=list(frames))
        card = screen.history(screen.parse("rsi>0"), frames, bench, eligible=nobody)
        self.assertEqual(card[5][2], 0)
        text = screen.format_result(screen.parse("rsi>0"), [], card)
        self.assertIn("yetersiz örnek", text)
        self.assertIn("2023-08", text)
        self.assertIn("30.10.2026", text)


class CommandTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.frames, self.bench = market()

    def answer(self, words, **kw):
        return screen.screen_text(words, live=lambda: (self.frames, self.bench), history_data=lambda: None,
                                  signal_path=self.tmp / "signal_log.csv", saved_path=self.tmp / "screens.csv",
                                  now=NOW, **kw)

    def test_alone_shows_examples(self):
        text = self.answer([])
        self.assertIn("/tara rsi<30", text)
        self.assertIn("ema20>ema50", text)

    def test_bad_expression(self):
        self.assertIn("Bilinmeyen alan", self.answer(["rsx<3"]))

    def test_live_record(self):
        from core.reports.forward import _read_log

        self.answer(["rsi<30"])
        rows = _read_log(self.tmp / "signal_log.csv")
        self.assertEqual({(r["source"], r["symbol"], r["view"]) for r in rows},
                         {("tara", s, "rsi<30") for s in expected_low_rsi(self.frames, self.bench)})
        self.assertTrue(all(r["details"] == "kriter=rsi<30" and r["data_date"] for r in rows))

    def test_saved_screens(self):
        saved = self.tmp / "screens.csv"
        self.assertIn("Kaydedildi", screen.save_text(["dusuk_rsi", "rsi<30"], path=saved, now=NOW))
        self.assertIn("Bilinmeyen alan", screen.save_text(["x", "rsx<30"], path=saved, now=NOW))
        self.assertIn("Kullanım", screen.save_text(["sadece_ad"], path=saved, now=NOW))
        self.assertIn("Ad", screen.save_text(["rsi<30", "rsi<30"], path=saved, now=NOW))
        self.assertIn("S00", self.answer(["dusuk_rsi"]))
        self.assertIn("dusuk_rsi: rsi<30", self.answer([]))
        before = saved.read_text(encoding="utf-8")
        screen.save_text(["dusuk_rsi", "rsi<25"], path=saved, now=NOW)  # replaced by a new row, nothing rewritten
        self.assertTrue(saved.read_text(encoding="utf-8").startswith(before))
        self.assertEqual(screen.load_saved(saved)["dusuk_rsi"], "rsi<25")


class PerformanceTest(unittest.TestCase):
    def test_per_criterion_results(self):
        from unittest import mock

        from core.reports import forward

        rows = pd.DataFrame([{"source": "tara", "view": "rsi<30", "day": date(2026, 10, d), "horizon": h,
                              "excess": 0.01 * (d % 3 - 1), "symbol": "S00.IS"}
                             for d in range(1, 28) for h in (5, 20)])
        with mock.patch.object(forward, "score_log", return_value=rows), \
                mock.patch.object(forward, "paper_vs_market", return_value=None):
            tmp = tempfile.TemporaryDirectory()
            self.addCleanup(tmp.cleanup)
            text = forward.forward_report(Path(tmp.name) / "s.csv", Path(tmp.name) / "e.csv",
                                          expectations_path=Path(tmp.name) / "x.csv")
        self.assertIn("/tara kriterleri", text)
        self.assertIn("rsi<30 · 5 seans", text)
        self.assertIn("rsi<30 · 20 seans", text)
        self.assertNotIn("/top, /analyze ve /watchscan kayıtları", text)  # tara is counted on its own


class BotTest(unittest.TestCase):
    def test_commands_are_wired(self):
        from unittest import mock

        from bot.handlers import COMMANDS, MENU
        from bot.start import HELP_TEXT
        from tests.test_bot_handlers import run as run_handler

        self.assertIn("tara", dict(MENU))
        self.assertIn("tara_kaydet", dict(MENU))
        self.assertIn("/tara", HELP_TEXT)
        self.assertIn("Örnekler", run_handler(dict(COMMANDS)["tara"], []))
        with mock.patch.object(screen, "screen_text", return_value="liste") as called:
            out = run_handler(dict(COMMANDS)["tara"], ["rsi<30"])
        called.assert_called_once_with(["rsi<30"])
        self.assertTrue(out.startswith("⏳") and out.endswith("liste"))
        self.assertIn("Kaydedildi", run_handler(dict(COMMANDS)["tara_kaydet"], ["dusuk", "rsi<30"]))


if __name__ == "__main__":
    unittest.main()
