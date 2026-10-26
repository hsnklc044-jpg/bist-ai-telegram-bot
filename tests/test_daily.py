import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

from core.ledger import Entry, append_entry
from core.ledger.paper import load_orders, place_order
from core.market import store
from core.market.calendar import ISTANBUL
from core.market.universe import BENCHMARK
from core.reports.daily import Paths, build_daily, read_equity, send_telegram, split_text
from core.signals_log import log_signal
from tests.helpers import offline_market

UNIVERSE = ["AAA.IS", "BBB.IS", "CCC.IS"]
NOW = datetime(2026, 10, 24, 12, 0, tzinfo=ISTANBUL)


class DailyReportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        self.paths = Paths(d / "ledger.csv", d / "orders.csv", d / "alerts.csv", d / "equity.csv")

    def tearDown(self):
        self.tmp.cleanup()

    def run_report(self):
        with offline_market():
            store.update([BENCHMARK, *UNIVERSE], now=NOW)
            return build_daily(self.paths, UNIVERSE)

    def test_empty_accounts(self):
        result = self.run_report()
        self.assertIn("Sanal hesap", result.text)
        self.assertNotIn("Gerçek hesap", result.text)  # no real positions -> section skipped
        self.assertIn("AL/SAT önerisi vermez", result.text)
        self.assertEqual(len(read_equity(self.paths.equity, "paper")), 1)

    def test_positions_alerts_and_paper_fill(self):
        append_entry(Entry(date(2026, 6, 1), "real", "AAA", "buy", 100, 50.0, 5.0), self.paths.ledger)
        place_order("BBB", "buy", 10, now=datetime(2026, 10, 20, 12, tzinfo=ISTANBUL),
                    orders_path=self.paths.orders, ledger_path=self.paths.ledger)

        first = self.run_report()
        self.assertIn("Gerçek hesap", first.text)
        self.assertIn("AAA: 100 adet", first.text)
        self.assertIn("Risk: 1 günlük kayıp", first.text)
        self.assertEqual(load_orders(self.paths.orders)[0].status, "filled")
        self.assertIn("Sanal emirler", first.text)

        # rerunning the same day sends nothing new and keeps one equity row per account/day
        second = self.run_report()
        self.assertEqual([e for e, _ in second.events], [])
        self.assertEqual(len(read_equity(self.paths.equity, "real")), 1)


class TelegramTest(unittest.TestCase):
    def test_send_uses_bot_api_and_splits(self):
        calls = []

        class Response:
            def raise_for_status(self):
                pass

        def post(url, json, timeout):
            calls.append((url, json))
            return Response()

        text = "\n".join(f"satır {i} " + "x" * 50 for i in range(200))
        send_telegram(text, "TOKEN", 42, post=post)
        self.assertGreater(len(calls), 1)
        self.assertTrue(all(c[0].endswith("/botTOKEN/sendMessage") for c in calls))
        self.assertTrue(all(c[1]["chat_id"] == 42 and len(c[1]["text"]) <= 4000 for c in calls))
        self.assertEqual("".join(c[1]["text"] for c in calls), text)

    def test_split_short(self):
        self.assertEqual(split_text("a\nb"), ["a\nb"])


class SignalLogTest(unittest.TestCase):
    def test_row_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "signals.csv"
            log_signal("analyze", "THYAO.IS", 72, "Pozitif", date(2026, 10, 23), 285.5, "rsi=55", path)
            log_signal("top", "ASELS.IS", None, "Nötr", None, path=path)
            lines = path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines[0], "logged_at,source,symbol,score,view,data_date,price,details")
        self.assertIn("THYAO.IS,72,Pozitif,2026-10-23,285.5,rsi=55", lines[1])
        self.assertEqual(len(lines), 3)


class UnrecordedActionTest(unittest.TestCase):
    def test_action_after_entry_without_ledger_row(self):
        from core.ledger import open_positions
        from core.market.corrections import CorporateAction
        from core.reports.daily import unrecorded_actions

        buy = Entry(date(2026, 10, 1), "paper", "SKBNK", "buy", 100, 4.6).validate()
        action = CorporateAction("SKBNK.IS", date(2026, 10, 22), kind="rights", ratio=0.4, note="%40 bedelli; x")
        pos = open_positions([buy], "paper")[0]
        self.assertEqual(unrecorded_actions(pos, [buy], [action]), ["22.10.2026 %40 bedelli"])

        rights = Entry(date(2026, 10, 24), "paper", "SKBNK", "rights", 40, 1.0).validate()
        pos = open_positions([buy, rights], "paper")[0]
        self.assertEqual(unrecorded_actions(pos, [buy, rights], [action]), [])

        old = CorporateAction("SKBNK.IS", date(2024, 6, 4), kind="rights", ratio=0.34)
        self.assertEqual(unrecorded_actions(pos, [buy], [old]), [])


class OutputEncodingTest(unittest.TestCase):
    def test_emoji_report_prints_on_a_cp1254_stream(self):
        import io

        from core.reports.daily import utf8_output

        raw = io.BytesIO()
        stream = io.TextIOWrapper(raw, encoding="cp1254")
        with self.assertRaises(UnicodeEncodeError):
            stream.write("🗓 rapor")
            stream.flush()
        raw2 = io.BytesIO()
        stream2 = io.TextIOWrapper(raw2, encoding="cp1254")
        utf8_output(stream2)
        stream2.write("🗓 rapor ✅")
        stream2.flush()
        self.assertEqual(raw2.getvalue().decode("utf-8"), "🗓 rapor ✅")


class MainTest(unittest.TestCase):
    def test_failure_is_written_to_the_log_file_with_exit_code_1(self):
        from unittest import mock

        from core.reports import daily

        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(daily, "_run", side_effect=RuntimeError("boom")):
            code = daily.main(["--no-update", "--log-dir", tmp])
            text = next(Path(tmp).glob("daily_*.log")).read_text(encoding="utf-8")
        self.assertEqual(code, 1)
        self.assertIn("HATA", text)
        self.assertIn("RuntimeError: boom", text)

    def test_success_writes_the_report(self):
        from unittest import mock

        from core.reports import daily

        fake = daily.DailyResult(date(2026, 10, 23), "🗓 rapor")
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(daily, "_run", return_value=fake):
            code = daily.main(["--no-update", "--log-dir", tmp])
            text = next(Path(tmp).glob("daily_*.log")).read_text(encoding="utf-8")
        self.assertEqual(code, 0)
        self.assertIn("🗓 rapor", text)


if __name__ == "__main__":
    unittest.main()


class ScoreRecordingFailureTest(unittest.TestCase):
    """A day missing from the live measurement must be said in that day's report, not only logged."""

    def test_failure_is_shown_in_the_report(self):
        from types import SimpleNamespace
        from unittest import mock

        from core.reports import daily

        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            paths = Paths(d / "ledger.csv", d / "orders.csv", d / "alerts.csv", d / "equity.csv")
            with offline_market(), \
                    mock.patch.object(daily, "Paths", lambda: paths), \
                    mock.patch.object(daily, "load_universe", return_value=UNIVERSE), \
                    mock.patch("core.reports.forward.log_daily_scores", side_effect=OSError("disk dolu")), \
                    mock.patch.object(daily, "_with_backup_line", side_effect=lambda t: t), \
                    mock.patch.object(daily, "_with_health_warnings", side_effect=lambda t: t):
                store.update([BENCHMARK, *UNIVERSE], now=NOW)
                result = daily._run_locked(SimpleNamespace(no_update=True, send=False, force=False))
        self.assertIn("Canlı ölçüm kaydı yazılamadı", result.text)
        self.assertIn("disk dolu", result.text)
        head, _, tail = result.text.rpartition(daily.DISCLAIMER)
        self.assertIn("Canlı ölçüm kaydı yazılamadı", head)  # before the closing disclaimer


class SplitLongLineTest(unittest.TestCase):
    def test_a_line_longer_than_the_limit_is_cut(self):
        text = "başlık\n" + "x" * 9000 + "\nson\n"
        parts = split_text(text, limit=4000)
        self.assertTrue(all(len(p) <= 4000 for p in parts))
        self.assertEqual("".join(parts), text)

    def test_bot_and_report_split_the_same_way(self):
        from bot.common import split_message

        text = "\n".join(f"satır {i} " + "y" * (i * 37 % 300) for i in range(400)) + "\n" + "z" * 5000
        self.assertEqual(split_message(text, 4000), split_text(text, 4000))
