"""
/tara as a command (core/screen/command.py, card.py): the message, the history card (never past
the holdout line, 30.10.2026), the live record, the saved screens and the bot wiring. A filter,
not advice.
"""

import re
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from core.backtest.run import SCREEN_END
from core.market.calendar import ISTANBUL
from core.screen import card, command, engine
from core.screen.language import parse

NOW = datetime(2026, 10, 28, 20, 0, tzinfo=ISTANBUL)


def walk(n, drift, seed, start=100.0, start_day="2023-01-02", volume=2e6):
    rng = np.random.default_rng(seed)
    close = pd.Series(start * np.exp(np.cumsum(rng.normal(drift, 0.01, n))),
                      index=pd.bdate_range(start_day, periods=n))
    return pd.DataFrame({"open": close * 0.999, "high": close * 1.01, "low": close * 0.99, "close": close,
                         "volume": volume}, index=close.index)


def market():
    """20 stocks; S00 and S01 fell hard in the last weeks (low RSI)."""
    frames = {}
    for i in range(20):
        df = walk(300, 0.0005, 10 + i)
        if i < 2:
            df.loc[df.index[-15:], ["open", "high", "low", "close"]] *= np.linspace(1, 0.7, 15)[:, None]
        frames[f"S{i:02d}.IS"] = df
    return frames, walk(300, 0.0, 99)


def low_rsi(frames, bench):
    return sorted(m.symbol for m in engine.run(parse("rsi<30 likidite=0"), frames, bench).matches)


class MessageTest(unittest.TestCase):
    def test_lines(self):
        frames, bench = market()
        result = engine.run(parse("rsi<30"), frames, bench)
        self.assertTrue({"S00.IS", "S01.IS"} <= {m.symbol for m in result.matches})
        text = command.format_result(result, None)
        self.assertIn("• S00", text)
        self.assertIn("RSI ", text)
        self.assertIn("1 ATR %", text)
        self.assertIn("2 ATR %", text)
        self.assertIn("likidite ", text)
        self.assertTrue(text.rstrip().endswith(command.DISCLAIMER))

    def test_words_length_and_overflow(self):
        frames, bench = market()
        result = engine.run(parse("rsi>0 ema20>0 macd>-1000 hacim_oran>0 atr_yuzde>0"), frames, bench)
        result.matches = result.matches * 3
        result.missing = [(f"X{i:02d}.IS", "son kapanış 24.10") for i in range(20)]
        text = command.format_result(result, {5: (0.001, 0.52, 1234), 20: (-0.002, 0.48, 1200)}, "not")
        self.assertIn(f"(+{len(result.matches) - 15} hisse daha: /tara_devam)", text)
        from bot.common import split_message

        self.assertTrue(all(len(part) <= 4096 for part in split_message(text)))
        body = text.replace(command.DISCLAIMER, "").lower()
        for word in (r"\bal\b", r"\bsat\b", r"\balın\b", r"\bsatın\b", r"en iyi", r"öneri", r"tavsiye", r"fırsat",
                     r"hedef fiyat", r"güçlü al"):
            self.assertIsNone(re.search(word, body), word)


class HistoryCardTest(unittest.TestCase):
    def frames_across_the_holdout(self):
        frames = {f"S{i:02d}.IS": walk(1030, 0.0003, 50 + i) for i in range(6)}
        return frames, walk(1030, 0.0, 77)

    def test_never_uses_data_after_the_holdout_line(self):
        frames, bench = self.frames_across_the_holdout()
        self.assertGreater(frames["S00.IS"].index[-1], pd.Timestamp(SCREEN_END))  # data runs past it
        q = parse("rsi>0")
        full = card.history(q, frames, bench)
        cut = card.history(q, {k: v.loc[:SCREEN_END] for k, v in frames.items()}, bench.loc[:SCREEN_END])
        self.assertEqual(full, cut)
        later = {k: v.copy() for k, v in frames.items()}  # change everything after the line: nothing moves
        for df in later.values():
            df.loc[df.index > pd.Timestamp(SCREEN_END), ["open", "close"]] *= 3
        self.assertEqual(card.history(q, later, bench), full)

    def test_counts_from_the_screening_start(self):
        frames, bench = self.frames_across_the_holdout()
        mean, hit, n = card.history(parse("rsi>0"), frames, bench)[5]
        self.assertGreater(n, 30)
        self.assertTrue(0 <= hit <= 1)
        early = {k: v.loc[:"2023-07-31"] for k, v in frames.items()}
        self.assertEqual(card.history(parse("rsi>0"), early, bench)[5][2], 0)

    def test_eligibility_rank_and_small_samples(self):
        frames, bench = self.frames_across_the_holdout()
        nobody = pd.DataFrame(False, index=bench.index, columns=list(frames))
        self.assertEqual(card.history(parse("rsi>0"), frames, bench, eligible=nobody)[5][2], 0)
        everyone = pd.DataFrame(True, index=bench.index, columns=list(frames))
        top = card.history(parse("gg_sira>80"), frames, bench, eligible=everyone)[5][2]
        allr = card.history(parse("gg_sira>-1"), frames, bench, eligible=everyone)[5][2]
        self.assertAlmostEqual(top / allr, 1 / 3, delta=0.01)  # of six stocks, ranks 83 and 100 are above 80
        frames2, bench2 = market()
        result = engine.run(parse("rsi>0"), frames2, bench2)
        text = command.format_result(result, {5: (None, None, 0), 20: (None, None, 12)})
        self.assertIn("5 seans: yetersiz örnek (0)", text)
        self.assertIn("20 seans: yetersiz örnek (12)", text)
        self.assertIn("2023-08", text)
        self.assertIn("30.10.2026", text)


class CommandTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.frames, self.bench = market()

    def answer(self, words):
        return command.screen_text(words, live=lambda symbols: (self.frames, self.bench), history_data=lambda: None,
                                   signal_path=self.tmp / "signal_log.csv", saved_path=self.tmp / "screens.csv",
                                   now=NOW, suspects=set())

    def test_alone_shows_examples(self):
        text = self.answer([])
        self.assertIn("/tara rsi<30", text)
        self.assertEqual(text.count("  /tara "), 5)
        self.assertIn("/tara_alanlar", text)

    def test_bad_expression(self):
        self.assertIn("'rsi' mi demek istediniz?", self.answer(["rsx<3"]))

    def test_live_record(self):
        from core.reports.forward import _read_log

        self.answer(["rsi<30"])
        rows = _read_log(self.tmp / "signal_log.csv")
        self.assertEqual({(r["source"], r["symbol"], r["view"]) for r in rows},
                         {("tara", s, "rsi<30") for s in low_rsi(self.frames, self.bench)})
        self.assertTrue(all(r["details"] == f"kriter=rsi<30;ozet={command.criterion_hash('rsi<30')}"
                            and r["data_date"] for r in rows))

    def test_saved_screens(self):
        saved = self.tmp / "screens.csv"
        self.assertIn("Kaydedildi", command.save_text(["dusuk_rsi", "rsi<30"], path=saved, now=NOW))
        self.assertIn("bilinmeyen alan", command.save_text(["x", "rsx<30"], path=saved, now=NOW))
        self.assertIn("Kullanım", command.save_text(["sadece_ad"], path=saved, now=NOW))
        self.assertIn("Ad", command.save_text(["rsi<30", "rsi<30"], path=saved, now=NOW))
        self.assertIn("S00", self.answer(["dusuk_rsi"]))
        self.assertIn("dusuk_rsi: rsi<30", self.answer([]))
        before = saved.read_text(encoding="utf-8")
        command.save_text(["dusuk_rsi", "rsi<25", "sirala=rsi"], path=saved, now=NOW)  # a new row, nothing rewritten
        self.assertTrue(saved.read_text(encoding="utf-8").startswith(before))
        self.assertEqual(command.load_saved(saved)["dusuk_rsi"], "rsi<25 sirala=rsi")


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
        from tests.test_bot_handlers import CHAT
        from tests.test_bot_handlers import run as run_handler

        self.assertIn("tara", dict(MENU))
        self.assertIn("tara_kaydet", dict(MENU))
        self.assertIn("/tara", HELP_TEXT)
        self.assertIn("Örnekler", run_handler(dict(COMMANDS)["tara"], []))
        with mock.patch.object(command, "screen_text", return_value="liste") as called:
            out = run_handler(dict(COMMANDS)["tara"], ["rsi<30"])
        called.assert_called_once_with(["rsi<30"], CHAT)
        self.assertTrue(out.startswith("⏳") and out.endswith("liste"))
        self.assertIn("Kaydedildi", run_handler(dict(COMMANDS)["tara_kaydet"], ["dusuk", "rsi<30"]))


if __name__ == "__main__":
    unittest.main()
