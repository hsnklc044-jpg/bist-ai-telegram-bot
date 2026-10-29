"""
Bağımsız doğrulama M15 (ORTA, docs/validation/M15.md): the corporate-action loader accepted rows that
corrupt prices silently. A duplicate row was applied twice (close 20 → 5 instead of 10), ratio −1
crashed the stock's read, an empty rights price became 1 TL, and sourceless or weekend rows passed.
Each is now refused with a reason the daily report shows; the repository file passes clean.
"""

import tempfile
import unittest
from pathlib import Path

from core.market import corrections

HEADER = "symbol,ex_date,kind,ratio,price,factor,source,note\n"


class LoaderTest(unittest.TestCase):
    def load(self, *rows):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ca.csv"
            path.write_text(HEADER + "".join(rows), encoding="utf-8")
            problems = []
            return corrections.load_corporate_actions(path, problems), problems

    def test_bad_rows_are_refused_with_a_reason(self):
        good = "AAA.IS,2026-03-02,bonus,1,,,https://kap,ok\n"
        actions, problems = self.load(
            good,
            good,  # duplicate
            "BBB.IS,2026-03-02,rights,-1,1,,https://kap,negatif oran\n",
            "CCC.IS,2026-03-02,rights,0.5,,,https://kap,fiyat yok\n",
            "DDD.IS,2026-03-02,bonus,1,,,,kaynaksız\n",
            "EEE.IS,2026-02-28,bonus,1,,,https://kap,cumartesi\n",
            "FFF.IS,2026-03-02,factor,,,-0.5,https://kap,negatif katsayı\n",
        )
        self.assertEqual([(a.symbol, a.kind) for a in actions], [("AAA.IS", "bonus")])
        self.assertEqual(len(problems), 6)
        joined = " ".join(problems)
        for word in ("tekrar", "oran", "fiyat", "kaynak", "hafta sonu", "katsayı"):
            self.assertIn(word, joined)

    def test_the_repository_file_is_clean(self):
        problems = []
        actions = corrections.load_corporate_actions(problems=problems)
        self.assertEqual(problems, [])
        self.assertGreaterEqual(len(actions), 29)


if __name__ == "__main__":
    unittest.main()
