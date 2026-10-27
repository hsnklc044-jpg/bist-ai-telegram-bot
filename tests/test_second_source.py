"""
SPOF Y-1: when Yahoo has no candle for the expected session, the day is not silent.
A short message gives the second source's (İş Yatırım) closes, for information only;
nothing from it is written to the price store (it has no open: paper fills and the live
measurement wait for Yahoo).
"""

import unittest
from datetime import date
from types import SimpleNamespace
from unittest import mock

import pandas as pd

from core.reports import daily

DAY = date(2026, 10, 28)


def isyatirim(rows: dict[date, tuple[float, float]]):
    """fetch_isyatirim stand-in: {day: (close, BIST 100)}."""

    def fetch(code, start, end, **kwargs):
        frame = pd.DataFrame(
            [{"date": pd.Timestamp(d), "close": c, "high": c, "low": c, "vwap": c, "volume_tl": 1.0, "index": i}
             for d, (c, i) in rows.items() if start <= d <= end])
        return frame.set_index("date") if not frame.empty else frame

    return fetch


class SecondSourceNoteTest(unittest.TestCase):
    def test_closes_of_held_stocks_and_the_index_labelled_as_information(self):
        note = daily._second_source_note(DAY, ["THYAO.IS"], fetch=isyatirim({DAY: (253.0, 11151.2)}))
        self.assertIn("Yahoo'dan 28.10.2026 kapanışı alınamadı", note)
        self.assertIn("İş Yatırım", note)
        self.assertIn("XU100 11.151", note)
        self.assertIn("THYAO 253,00", note)
        self.assertIn("yalnız bilgi", note)
        self.assertTrue(note.rstrip().endswith(daily.DISCLAIMER))

    def test_no_row_for_that_day_means_no_message(self):
        self.assertIsNone(daily._second_source_note(DAY, ["THYAO.IS"],
                                                    fetch=isyatirim({date(2026, 10, 27): (250.0, 11000.0)})))

    def test_second_source_down_means_no_message(self):
        def down(*args, **kwargs):
            raise ConnectionError("isyatirim down")

        self.assertIsNone(daily._second_source_note(DAY, ["THYAO.IS"], fetch=down))


class StaleDaySendsSecondSourceOnceTest(unittest.TestCase):
    def run_stale(self, send, yahoo="failed"):
        fake = daily.DailyResult(date(2026, 10, 27), "dünkü rapor")
        args = SimpleNamespace(no_update=False, send=True, force=False)
        settings = SimpleNamespace(bot_token="x", chat_id=1)
        with mock.patch.object(daily, "update_prices", return_value={daily.BENCHMARK: yahoo}), \
                mock.patch.object(daily, "symbols_to_update", return_value=[daily.BENCHMARK]), \
                mock.patch.object(daily, "_record_freshness"), \
                mock.patch.object(daily, "build_daily", return_value=fake), \
                mock.patch.object(daily, "_record_scores", return_value=""), \
                mock.patch.object(daily, "already_sent", return_value=True), \
                mock.patch.object(daily, "_not_sent_reason", return_value=("stale", "beklenen 28.10.2026")), \
                mock.patch.object(daily, "last_final_session_date", return_value=DAY), \
                mock.patch.object(daily, "_held_symbols", return_value=["THYAO.IS"]), \
                mock.patch.object(daily, "_second_source_note", return_value="ikinci kaynak notu"), \
                mock.patch("core.infrastructure.settings.require_bot_settings", return_value=settings), \
                mock.patch.object(daily, "send_telegram", side_effect=send) as sent:
            result = daily._run_locked(args)
        return result, sent

    def test_sent_once_per_missing_day_and_status_stays_stale(self):
        result, sent = self.run_stale(None)
        self.assertEqual(result.status, "stale")  # the report SLO still counts the day as missed
        sent.assert_called_once_with("ikinci kaynak notu", "x", 1)
        self.assertIn("ikinci kaynak", result.note)

        _, sent_again = self.run_stale(None)  # the task runs again the same evening
        sent_again.assert_not_called()

    def test_yahoo_only_late_sends_nothing(self):
        """Öz-denetim 2, Ö6: Yahoo answered but without today's candle (late, not down): wait for it."""
        for status in ("incremental", "fresh"):
            with self.subTest(status):
                result, sent = self.run_stale(None, yahoo=status)
                sent.assert_not_called()
                self.assertEqual(result.status, "stale")

    def test_a_failed_send_never_turns_a_stale_day_into_an_error(self):
        result, _ = self.run_stale(ConnectionError("Telegram HTTP 502"))
        self.assertEqual(result.status, "stale")


if __name__ == "__main__":
    unittest.main()
