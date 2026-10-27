"""CHARTER C2: weekly scan for corporate-action suspects (unadjusted bonus/rights issues, splits)."""

import unittest

from core.market import quality


def q(symbol, jumps=(), breaches=()):
    r = quality.SymbolQuality(symbol=symbol, candles=100, first="2026-01-02", last="2026-10-30")
    r.jumps = [quality.Jump(d, c, round(1 + c, 4)) for d, c in jumps]
    r.breaches = [quality.Jump(d, c, round(1 + c, 4)) for d, c in breaches]
    return r


class RecentSuspectsTest(unittest.TestCase):
    def test_only_new_moves_and_known_actions_left_out(self):
        report = [
            q("AAA.IS", jumps=[("2026-10-28", -0.45), ("2026-03-02", -0.5)]),  # old one is not "new"
            q("BBB.IS", breaches=[("2026-10-29", -0.14)]),
            q("CCC.IS", jumps=[("2026-10-27", -0.6)]),  # already in corporate_actions.csv
        ]
        found = quality.recent_suspects(report, since="2026-10-24", known={("CCC.IS", "2026-10-27")})
        self.assertEqual([(s["symbol"], s["date"], s["kind"]) for s in found],
                         [("AAA.IS", "2026-10-28", "sıçrama"), ("BBB.IS", "2026-10-29", "limit aşımı")])
        self.assertEqual(found[0]["suggested_factor"], 0.55)

    def test_text_says_what_to_check(self):
        text = quality.format_suspects([{"symbol": "AAA.IS", "date": "2026-10-28", "change": -0.45,
                                         "kind": "sıçrama", "suggested_factor": 0.55}], "24.10.2026")
        self.assertIn("AAA 28.10.2026 -45.0% sıçrama", text)
        self.assertIn("KAP", text)
        self.assertIn("uygulanmadı", text)
        self.assertIn("yeni şüphe yok", quality.format_suspects([], "24.10.2026"))


if __name__ == "__main__":
    unittest.main()
