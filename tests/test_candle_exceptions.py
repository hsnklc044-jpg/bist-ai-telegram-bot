"""
Veri borcu (Özellik Talimatı A'nın giriş kapısı, 28.10.2026): two ±20% "jumps" are no corporate
action. ASUZU 27.06.2022 is one broken Yahoo candle (open=high=low=close=35.13; İş Yatırım 39.27):
it is DROPPED. GOLTS 08.04→15.04.2024 is a real move over a session Yahoo does not have (09.04
half day; two limit-ups): it is a REAL MOVE, not a data jump. data/candle_exceptions.csv holds
such rows, each with its source; nothing is guessed.
"""

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from core.market import corrections, quality
from core.screen import elimination

HEADER = "symbol,date,action,source,note\n"


def frame(closes, start="2024-04-01"):
    index = pd.bdate_range(start, periods=len(closes))
    close = pd.Series(closes, index=index, dtype=float)
    return pd.DataFrame({"open": close, "high": close * 1.01, "low": close * 0.99, "close": close, "volume": 1e6})


class Files(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "candle_exceptions.csv"

    def write(self, *rows):
        self.path.write_text(HEADER + "".join(rows), encoding="utf-8")
        return corrections.load_candle_exceptions(self.path)


class LoadTest(Files):
    def test_rows_need_a_known_action_and_a_source(self):
        problems = []
        self.path.write_text(HEADER + "X.IS,2024-04-03,drop,https://kaynak,bozuk mum\n"
                                      "X.IS,2024-04-04,sil,https://kaynak,bilinmeyen eylem\n"
                                      "X.IS,2024-04-05,drop,,kaynaksız\n", encoding="utf-8")
        rows = corrections.load_candle_exceptions(self.path, problems)
        self.assertEqual([(r.symbol, r.date.isoformat(), r.action) for r in rows], [("X.IS", "2024-04-03", "drop")])
        self.assertEqual(len(problems), 2)


class DropTest(Files):
    def test_a_broken_candle_is_removed_before_anything_else(self):
        df = frame([35.73, 35.13, 42.52, 40.83])  # ASUZU-like: the second candle is broken
        rows = self.write(f"X.IS,{df.index[1].date()},drop,datacheck 28.10.2026,flat candle\n")
        cleaned = corrections.apply_candle_exceptions(df, "X.IS", rows)
        self.assertEqual(len(cleaned), 3)
        self.assertNotIn(df.index[1], cleaned.index)
        self.assertEqual(len(corrections.apply_candle_exceptions(df, "Y.IS", rows)), 4)  # another stock

    def test_quality_no_longer_sees_a_jump(self):
        df = frame([35.73, 35.13, 42.52, 40.83])
        self.assertTrue(quality.check_symbol(df, "X.IS").jumps)
        rows = self.write(f"X.IS,{df.index[1].date()},drop,datacheck,flat\n")
        self.assertFalse(quality.check_symbol(corrections.apply_candle_exceptions(df, "X.IS", rows), "X.IS").jumps)


class RealMoveTest(Files):
    def test_neither_quality_nor_the_data_elimination_counts_it(self):
        df = frame([417.12] * 30 + [504.51] * 5)  # GOLTS-like: +21% over a missing half day
        day = df.index[30].date()
        self.assertEqual(len(quality.check_symbol(df, "X.IS").jumps), 1)
        rows = self.write(f"X.IS,{day},real_move,datacheck 28.10.2026,two limit-ups over 09.04\n")
        self.assertEqual(quality.check_symbol(df, "X.IS", exceptions=rows).jumps, [])
        check = elimination.frame(df, "X.IS", df.index, [], exceptions=rows)
        self.assertEqual(check["jump"].iloc[-1], "")
        self.assertNotEqual(elimination.frame(df, "X.IS", df.index, [])["jump"].iloc[-1], "")

    def test_the_repository_rows_are_sourced(self):
        rows = corrections.load_candle_exceptions()
        found = {(r.symbol, r.date.isoformat(), r.action) for r in rows}
        self.assertIn(("ASUZU.IS", "2022-06-27", "drop"), found)
        self.assertIn(("GOLTS.IS", "2024-04-15", "real_move"), found)
        self.assertTrue(all(r.source for r in rows))


if __name__ == "__main__":
    unittest.main()
