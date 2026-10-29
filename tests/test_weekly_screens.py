"""
İleri hedef 3: the Friday report lists the user's saved screens with their live results (the
"tara" records of the same criterion): the 20-session (else 5) excess over XU100, or "veri birikiyor"
under 30 matured records. The saved screens are personal (PC only), so this runs in the report.
"""

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from core.market.universe import BENCHMARK
from core.reports import forward
from core.screen import command
from core.screen.language import parse
from core.signals_log import log_signal
from tests.helpers import make_ohlcv


class WeeklyScreensTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.log, self.saved = self.root / "signal_log.csv", self.root / "screens.csv"
        self.frames = {BENCHMARK: make_ohlcv(rows=300, seed=99)}
        for i in range(6):
            self.frames[f"S{i}.IS"] = make_ohlcv(rows=300, seed=20 + i)
        self.bars = lambda s: self.frames.get(s, pd.DataFrame())

    def test_lines(self):
        command.save_text(["dusuk", "rsi<30"], path=self.saved)
        command.save_text(["trend", "ema20>ema50"], path=self.saved)
        text = parse("rsi<30").text
        index = self.frames["S0.IS"].index
        for i in range(150, 260, 3):
            for s in ("S0.IS", "S1.IS"):
                log_signal("tara", s, None, text, index[i].date(), path=self.log)
        lines = forward.saved_screen_lines(self.log, self.saved, bars=self.bars)
        joined = "\n".join(lines)
        self.assertIn("📌 Kayıtlı taramalar", joined)
        self.assertIn("dusuk (rsi<30): 20 seans", joined)
        self.assertIn("trend (ema20>ema50): veri birikiyor (0/30)", joined)

    def test_no_saved_screen_no_section(self):
        self.assertEqual(forward.saved_screen_lines(self.log, self.saved, bars=self.bars), [])

    def test_friday_line_includes_it(self):
        command.save_text(["dusuk", "rsi<30"], path=self.saved)
        line = forward.weekly_line(self.log, self.root / "equity.csv", bars=self.bars, saved_path=self.saved)
        self.assertIn("📌 Kayıtlı taramalar", line)


if __name__ == "__main__":
    unittest.main()
