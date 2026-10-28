"""
/tara_sanal (/tara Aşama 4d, DECISIONS K-43): off by default; when on, a saved screen or template
runs in a measurement-only book with rules written in advance (equal weight, at most 5 positions,
20 sessions, 2 ATR stop, next open). It never touches the personal paper orders or the ledger.
"""

import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

from core.market.calendar import ISTANBUL
from core.screen import command, virtual
from core.screen.language import parse

NOW = datetime(2026, 10, 28, 20, 0, tzinfo=ISTANBUL)


def flat(n=80, start_day="2026-06-01", price=100.0):
    index = pd.bdate_range(start_day, periods=n)
    close = pd.Series(price, index=index, dtype=float)
    return pd.DataFrame({"open": close, "high": close * 1.01, "low": close * 0.99, "close": close,
                         "volume": 1e6}, index=index)


def signal_frames(symbols, day_index=40):
    """Each stock jumps 10% on one day (getiri(2) > 5 holds that day only)."""
    frames = {}
    for i, s in enumerate(symbols):
        df = flat()
        df.iloc[day_index:, :4] *= 1.10
        frames[s] = df
    return frames


class Files(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        d = Path(tmp.name)
        self.path, self.saved = d / "virtual.csv", d / "screens.csv"
        command.save_text(["sicrama", "getiri(2)>5", "likidite=0"], path=self.saved, now=NOW)

    def cmd(self, *words):
        return virtual.command_text(list(words), path=self.path, saved_path=self.saved, now=NOW)


class OnOffTest(Files):
    def test_off_by_default(self):
        self.assertIn("kapalı (varsayılan)", self.cmd())
        self.assertEqual(virtual.books(self.path), {})
        lines = virtual.report_lines(self.path, live=mock.Mock(side_effect=AssertionError("no prices when off")))
        self.assertIn("Kapalı (varsayılan)", "\n".join(lines))

    def test_on_list_off(self):
        self.assertIn("yok", self.cmd("bilinmeyen"))
        self.assertIn("açıldı: sicrama", self.cmd("sicrama"))
        self.assertIn("SANAL", self.cmd("sicrama", "kapat").upper() + self.cmd())
        self.assertIn("zaten kapalı", self.cmd("sicrama", "kapat"))
        self.assertIn("açıldı", self.cmd("duseni_kiran"))  # a template too
        self.assertIn("duseni_kiran", self.cmd())
        self.assertIn("Kullanım", self.cmd("a", "b", "c"))

    def test_criterion_is_frozen_when_turned_on(self):
        self.cmd("sicrama")
        command.save_text(["sicrama", "rsi<30"], path=self.saved, now=NOW)
        self.assertEqual(virtual.books(self.path)["sicrama"], ("getiri(2)>5 likidite=0", date(2026, 10, 28)))

    def test_limit(self):
        for name in ("sicrama", "duseni_kiran", "bebek_teknik"):
            self.cmd(name)
        self.assertIn("En fazla", self.cmd("basit_teknik"))

    def test_never_touches_paper_orders_or_the_ledger(self):
        from core.config import paths

        source = Path(virtual.__file__).read_text(encoding="utf-8")
        for word in ("PAPER_ORDERS_FILE", "LEDGER_FILE", "core.ledger"):
            self.assertNotIn(word, source.split('"""', 2)[2])  # outside the docstring
        with mock.patch.object(paths, "PAPER_ORDERS_FILE", self.path.parent / "paper_orders.csv"):
            self.cmd("sicrama")
            frames = signal_frames(["A.IS"])
            virtual.report_lines(self.path, live=lambda s: (frames, flat()), today=date(2026, 9, 30))
        self.assertFalse((self.path.parent / "paper_orders.csv").exists())


class SimulateTest(unittest.TestCase):
    query = parse("getiri(2)>5 likidite=0")

    def test_enters_next_open_and_leaves_after_twenty_sessions(self):
        frames, bench = signal_frames(["A.IS"]), flat()
        book = virtual.simulate(self.query, frames, bench, date(2026, 6, 1))
        (trade,) = book.trades
        self.assertEqual(trade.entry_day, frames["A.IS"].index[41].date())  # never the signal day's own price
        self.assertEqual(trade.exit_day, frames["A.IS"].index[60].date())
        self.assertEqual(trade.reason, "süre")
        self.assertAlmostEqual(trade.result, (1 - virtual.COST) / (1 + virtual.COST) - 1)
        self.assertLess(book.value, 1.0)  # flat prices: only the costs
        self.assertGreater(trade.entry, frames["A.IS"]["close"].iloc[39])  # bought after the jump, at its price

    def test_at_most_five_positions_equal_weight(self):
        frames = signal_frames([f"S{i}.IS" for i in range(7)])
        book = virtual.simulate(self.query, frames, flat(), date(2026, 6, 1))
        self.assertEqual([t.symbol for t in book.trades], [f"S{i}.IS" for i in range(5)])  # alphabetical
        self.assertAlmostEqual(book.value, (1 - virtual.COST) / (1 + virtual.COST), places=9)

    def test_stop(self):
        frames = signal_frames(["A.IS"])
        frames["A.IS"].iloc[45:, :4] *= 0.9  # well below entry − 2 ATR
        (trade,) = virtual.simulate(self.query, frames, flat(), date(2026, 6, 1)).trades
        self.assertEqual(trade.reason, "stop")
        self.assertEqual(trade.exit_day, frames["A.IS"].index[45].date())

    def test_signals_before_the_start_are_ignored(self):
        frames = signal_frames(["A.IS"])
        start = frames["A.IS"].index[50].date()
        self.assertEqual(virtual.simulate(self.query, frames, flat(), start).trades, [])

    def test_no_look_ahead(self):
        frames, bench = signal_frames(["A.IS"]), flat()
        end = frames["A.IS"].index[70].date()
        before = virtual.simulate(self.query, frames, bench, date(2026, 6, 1), end)
        later = {k: v.copy() for k, v in frames.items()}
        later["A.IS"].iloc[71:, :4] *= 3
        self.assertEqual(virtual.simulate(self.query, later, bench, date(2026, 6, 1), end).trades, before.trades)

    def test_report_shows_the_label_and_accumulates(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path, saved = Path(tmp.name) / "v.csv", Path(tmp.name) / "s.csv"
        command.save_text(["sicrama", "getiri(2)>5", "likidite=0"], path=saved, now=NOW)
        virtual.command_text(["sicrama"], path=path, saved_path=saved,
                             now=datetime(2026, 6, 1, 20, 0, tzinfo=ISTANBUL))
        frames = signal_frames(["A.IS"])
        with mock.patch("core.screen.universe.symbols", return_value=["A.IS"]):
            text = "\n".join(virtual.report_lines(path, live=lambda s: (frames, flat())))
        self.assertIn("SANAL", text)
        self.assertIn("1 kapanmış işlem", text)
        self.assertIn("veri birikiyor (1/30", text)
        self.assertTrue(np.isfinite(virtual.simulate(self.query, frames, flat(), date(2026, 6, 1)).value))


class WiringTest(unittest.TestCase):
    def test_performance_bot_backup(self):
        from bot.handlers import COMMANDS, MENU
        from bot.start import HELP_TEXT
        from core import backup
        from core.config.paths import ROOT_DIR, SCREEN_VIRTUAL_FILE
        from core.reports import forward, health

        self.assertIn("tara_sanal", dict(COMMANDS))
        self.assertIn("tara_sanal", dict(MENU))
        self.assertIn("/tara_sanal", HELP_TEXT)
        self.assertIn(SCREEN_VIRTUAL_FILE, backup.PERSONAL_FILES)
        self.assertIn(SCREEN_VIRTUAL_FILE, health.SCHEMAS)
        self.assertIn("data/screen_virtual.csv", (ROOT_DIR / ".gitignore").read_text(encoding="utf-8"))
        rows = pd.DataFrame(columns=["source", "view", "day", "horizon", "excess", "symbol"])
        with mock.patch.object(forward, "score_log", return_value=rows), \
                mock.patch.object(forward, "paper_vs_market", return_value=None):
            tmp = tempfile.TemporaryDirectory()
            self.addCleanup(tmp.cleanup)
            text = forward.forward_report(Path(tmp.name) / "s.csv", Path(tmp.name) / "e.csv",
                                          expectations_path=Path(tmp.name) / "x.csv")
        self.assertIn("🧪 Sanal köprü", text)
        self.assertLess(text.index("🧪 Sanal köprü"), text.index("💼 Sanal hesap"))


if __name__ == "__main__":
    unittest.main()
