"""Ö67: core/watchlist/scanner.py had no test of its own (ROADMAP öz-denetim 11)."""

import unittest
from unittest import mock

from core.watchlist import scanner


def result(signal="BUY", score=7, trend="yukarı"):
    return {"signal": signal, "score": score, "trend": trend}


class WatchlistScanTest(unittest.TestCase):
    def test_empty_watchlist(self):
        with mock.patch.object(scanner, "get_watchlist", return_value=[]):
            self.assertEqual(scanner.generate_watchlist_scan(1), "📌 Watchlist boş.")

    def test_lines_labels_and_one_record_per_analysed_stock(self):
        analyses = {"AAA": result(), "BBB": None, "CCC": result("UNKNOWN", 3, "yatay")}
        with mock.patch.object(scanner, "get_watchlist", return_value=["AAA", "BBB", "CCC"]), \
                mock.patch.object(scanner, "analyze_stock", side_effect=analyses.get), \
                mock.patch.object(scanner, "log_analysis") as log:
            text = scanner.generate_watchlist_scan(42)
        self.assertTrue(text.startswith("📌 WATCHLIST SCAN"))
        self.assertIn("📈 AAA\n📊 Görünüm : Pozitif (skor 7)\n📊 Trend : yukarı", text)
        self.assertNotIn("BBB", text)  # no data: skipped, not guessed
        self.assertIn("Görünüm : UNKNOWN (skor 3)", text)  # an unknown label is shown as it is
        self.assertEqual([c.args[0] for c in log.call_args_list], ["watchscan", "watchscan"])
        self.assertEqual(log.call_args_list[0].args[2], "Pozitif")


if __name__ == "__main__":
    unittest.main()
