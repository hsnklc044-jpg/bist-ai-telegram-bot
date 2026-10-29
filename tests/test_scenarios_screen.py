"""
Özellik B §3: the templates as /tara conditions, senaryo(destek_tepkisi) etc. Each day's value is
the template's own day-by-day signal (no look-ahead), so the live list and the card agree.
"""

import unittest

from core.analytics import scenarios as S
from core.screen import fields as F
from core.screen.language import ScreenError, parse
from tests.test_scenarios import walk


class LanguageTest(unittest.TestCase):
    def test_syntax(self):
        q = parse("senaryo(destek_tepkisi) rsi<40")
        self.assertEqual(q.text, "senaryo(destek_tepkisi) ve rsi<40")
        self.assertIn("senaryo_destek_tepkisi", q.fields)
        for name in S.TEMPLATES:
            self.assertEqual(parse(f"senaryo({name})").text, f"senaryo({name})")

    def test_errors(self):
        with self.assertRaises(ScreenError) as caught:
            parse("senaryo(boga)")
        self.assertIn("destek_tepkisi", str(caught.exception))
        with self.assertRaises(ScreenError):
            parse("senaryo_destek_tepkisi>0")  # only through senaryo(...)


class ValueTest(unittest.TestCase):
    def test_equals_the_template_signal(self):
        df = walk()
        table = F.table(df, walk(seed=9)["close"], ["senaryo_destek_tepkisi", "senaryo_trend_geri_cekilme"])
        signals = S.signals(df)
        for name in ("destek_tepkisi", "trend_geri_cekilme"):
            got = table[f"senaryo_{name}"].fillna(0).astype(bool)
            self.assertTrue((got == signals[name]["ok"]).all(), name)
        q = parse("senaryo(trend_geri_cekilme)")
        self.assertEqual(int(q.mask(table).sum()), int(signals["trend_geri_cekilme"]["ok"].sum()))


if __name__ == "__main__":
    unittest.main()
