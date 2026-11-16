"""
Ö56: on 16.11.2026 Yahoo answered empty for every symbol at 18:30-18:35 and was back at 18:39.
The run ended 'stale' with no Telegram message and no second attempt; the report went out only
after a manual run at 18:41. Now: one retry after STALE_RETRY_WAIT (the Windows task stops after
30 minutes), and if the day is still missing and nothing went out, one line to Telegram.
"""

from __future__ import annotations

import contextlib
import unittest
from datetime import date
from types import SimpleNamespace
from unittest import mock

from core.reports import daily

DAY = date(2026, 11, 16)


def stale(yahoo_down=True, note="beklenen 16.11.2026 kapanışı, veri 13.11.2026"):
    return daily.DailyResult(date(2026, 11, 13), "", status="stale", note=note, yahoo_down=yahoo_down)


class StaleRetryTest(unittest.TestCase):
    def run_it(self, results, args=None):
        args = args or SimpleNamespace(no_update=False, send=True, force=False)
        settings = SimpleNamespace(bot_token="x", chat_id=1)
        sleep = mock.Mock()
        with mock.patch.object(daily, "report_lock", contextlib.nullcontext), \
                mock.patch.object(daily, "_run_locked", side_effect=results) as runs, \
                mock.patch.object(daily, "last_final_session_date", return_value=DAY), \
                mock.patch("core.infrastructure.settings.require_bot_settings", return_value=settings), \
                mock.patch.object(daily, "send_telegram") as sent:
            result = daily._run(args, sleep=sleep)
        return result, runs, sleep, sent

    def test_yahoo_down_is_retried_once_and_the_report_goes_out(self):
        ok = daily.DailyResult(DAY, "rapor", status="sent")
        result, runs, sleep, sent = self.run_it([stale(), ok])
        self.assertEqual(result.status, "sent")
        self.assertEqual(runs.call_count, 2)
        sleep.assert_called_once_with(daily.STALE_RETRY_WAIT)
        self.assertLess(daily.STALE_RETRY_WAIT, 20 * 60)  # task limit 30 min; a run takes ~5 (16.11: 303 s)
        sent.assert_not_called()

    def test_still_missing_and_nothing_sent_means_one_line_once(self):
        result, runs, _, sent = self.run_it([stale(), stale()])
        self.assertEqual(result.status, "stale")  # the report SLO still counts the day as missed
        self.assertEqual(runs.call_count, 2)
        sent.assert_called_once()
        text = sent.call_args.args[0]
        self.assertEqual(text.count("\n"), 0)
        self.assertIn("16.11.2026", text)
        self.assertIn("Yahoo", text)

        _, _, _, sent_again = self.run_it([stale(), stale()])  # the bot's catch-up run, same evening
        sent_again.assert_not_called()

    def test_no_line_when_the_second_source_already_told(self):
        told = stale(note="beklenen 16.11.2026; ikinci kaynak bilgisi gönderildi")
        _, _, _, sent = self.run_it([told, told])
        sent.assert_not_called()

    def test_yahoo_only_late_is_not_retried(self):
        result, runs, sleep, sent = self.run_it([stale(yahoo_down=False)])
        self.assertEqual(runs.call_count, 1)
        sleep.assert_not_called()
        sent.assert_not_called()

    def test_manual_runs_without_update_or_send_are_not_retried(self):
        for args in (SimpleNamespace(no_update=True, send=True, force=False),
                     SimpleNamespace(no_update=False, send=False, force=False)):
            with self.subTest(args):
                _, runs, sleep, sent = self.run_it([stale()], args=args)
                self.assertEqual(runs.call_count, 1)
                sleep.assert_not_called()
                sent.assert_not_called()

    def test_a_failed_warning_never_turns_a_stale_day_into_an_error(self):
        settings = SimpleNamespace(bot_token="x", chat_id=1)
        with mock.patch.object(daily, "report_lock", contextlib.nullcontext), \
                mock.patch.object(daily, "_run_locked", side_effect=[stale(), stale()]), \
                mock.patch.object(daily, "last_final_session_date", return_value=DAY), \
                mock.patch("core.infrastructure.settings.require_bot_settings", return_value=settings), \
                mock.patch.object(daily, "send_telegram", side_effect=ConnectionError("502")):
            result = daily._run(SimpleNamespace(no_update=False, send=True, force=False), sleep=mock.Mock())
        self.assertEqual(result.status, "stale")


if __name__ == "__main__":
    unittest.main()
