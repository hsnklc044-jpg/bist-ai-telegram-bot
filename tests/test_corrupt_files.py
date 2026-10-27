"""
Damaged personal files (a half-written last line, garbage, an empty file).

- Ledger, paper orders, watchlist: never guessed around and never
  overwritten; the error names the file and the line and says how to fix it.
- Equity and alert logs: the daily report still goes out with a warning,
  and the damaged file is left as it is.
- Live measurement log: unreadable rows are counted (Kayıt sağlığı), the
  rest is scored.
- The bot answers with the warning instead of a generic error.
"""

import asyncio
import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from core.alerts.log import FIELDS as ALERT_FIELDS
from core.alerts.log import open_alerts
from core.infrastructure.exceptions import PersonalFileError
from core.ledger import Entry, append_entry, load_ledger
from core.ledger.paper import load_orders
from core.market import store
from core.market.universe import BENCHMARK
from core.reports.daily import Paths, build_daily, read_equity
from core.reports.forward import score_log
from core.signals_log import audit_log
from tests.helpers import make_ohlcv, offline_market

LEDGER = "id,date,account,symbol,side,quantity,price,fee,note\n1,2026-06-01,real,AAA.IS,buy,100,50,5,\n"
ORDERS = ("id,created_at,symbol,side,quantity,status,fill_date,fill_price,note\n"
          "1,2026-10-20T12:00:00+03:00,BBB.IS,buy,10,pending,,,\n")
EQUITY = "date,account,value,cash,invested,positions\n2026-10-22,paper,100000.00,100000.00,0.00,0\n"
SIGNAL = ("logged_at,source,symbol,score,view,data_date,price,details\n"
          "2026-10-01T18:30:00+03:00,daily,AAA.IS,80,Pozitif,2026-10-01,10,\n")
ALERTS = (",".join(ALERT_FIELDS) + "\n"
          + "2026-10-26T18:30:00+03:00,2026-10-26,real,AAA.IS,stop,open,2,1,1,x\n")


def half(good: str) -> str:
    return good + good.splitlines()[1][:12]  # the process died while writing a row


def garbage(good: str) -> str:
    return good + "\x00\x00bozuk,,,\n"


class Temp(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def write(self, name, text):
        path = self.root / name
        path.write_text(text, encoding="utf-8")
        return path

    def assertWarns_(self, exc, name, line=None):
        text = str(exc)
        self.assertIn(name, text)
        if line is not None:
            self.assertIn(f"satır {line}", text)
        self.assertIn("Dosyaya dokunulmadı", text)


class StrictFilesTest(Temp):
    def test_ledger(self):
        for make, line in ((half, 3), (garbage, 3)):
            with self.subTest(make.__name__):
                path = self.write("ledger.csv", make(LEDGER))
                with self.assertRaises(PersonalFileError) as ctx:
                    load_ledger(path)
                self.assertWarns_(ctx.exception, "ledger.csv", line)
        path = self.write("ledger.csv", "")
        with self.assertRaises(PersonalFileError) as ctx:
            load_ledger(path)
        self.assertIn("boş", str(ctx.exception))

    def test_ledger_is_never_extended_past_a_damaged_row(self):
        path = self.write("ledger.csv", half(LEDGER))
        before = path.read_bytes()
        with self.assertRaises(PersonalFileError):
            append_entry(Entry(date(2026, 6, 2), "real", "AAA", "buy", 1, 50.0, 0.0), path)
        self.assertEqual(path.read_bytes(), before)

    def test_orders(self):
        for make, line in ((half, 3), (garbage, 3)):
            with self.subTest(make.__name__):
                path = self.write("paper_orders.csv", make(ORDERS))
                with self.assertRaises(PersonalFileError) as ctx:
                    load_orders(path)
                self.assertWarns_(ctx.exception, "paper_orders.csv", line)
        with self.assertRaises(PersonalFileError):
            load_orders(self.write("paper_orders.csv", ""))

    def test_header_only_is_a_valid_empty_file(self):
        self.assertEqual(load_ledger(self.write("ledger.csv", LEDGER.splitlines()[0] + "\n")), [])
        self.assertEqual(load_orders(self.write("paper_orders.csv", ORDERS.splitlines()[0] + "\n")), [])

    def test_equity_and_alert_logs(self):
        for name, good, read in (("equity_log.csv", EQUITY, lambda p: read_equity(p, "paper")),
                                 ("alerts_log.csv", ALERTS, open_alerts)):
            for make in (half, garbage, lambda g: ""):
                with self.subTest(name):
                    path = self.write(name, make(good))
                    with self.assertRaises(PersonalFileError) as ctx:
                        read(path)
                    self.assertWarns_(ctx.exception, name)

    def test_watchlist_is_not_overwritten(self):
        from core.watchlist import repository, service

        path = self.write("watchlist.json", '{"1": {"symbols": ["EREGL.IS"]')  # cut off
        before = path.read_bytes()
        with mock.patch.object(repository, "WATCHLIST_FILE", path):
            with self.assertRaises(PersonalFileError) as ctx:
                repository.load_watchlist()
            self.assertWarns_(ctx.exception, "watchlist.json")
            with self.assertRaises(ValueError):  # /watchadd shows the message (ValueError is answered)
                service.add_symbol(1, "THYAO")
        self.assertEqual(path.read_bytes(), before)


class SignalLogTest(Temp):
    def test_unreadable_rows_are_counted_and_the_rest_scored(self):
        path = self.write("signal_log.csv", half(SIGNAL))
        scored = score_log(path, bars=lambda s: make_ohlcv(rows=300))
        self.assertEqual(set(scored["day"]), {date(2026, 10, 1)})
        self.assertEqual(audit_log(path).bad_rows, 1)

    def test_empty_file_is_a_problem(self):
        audit = audit_log(self.write("signal_log.csv", ""))
        self.assertTrue(audit.problems)
        self.assertIn("boş", audit.text())


class DailyReportTest(Temp):
    def paths(self):
        return Paths(self.root / "ledger.csv", self.root / "orders.csv", self.root / "alerts.csv",
                     self.root / "equity.csv")

    def run_report(self, paths):
        with offline_market():
            store.update([BENCHMARK, "AAA.IS"])
            return build_daily(paths, ["AAA.IS"])

    def test_damaged_logs_give_a_warning_and_stay_untouched(self):
        paths = self.paths()
        append_entry(Entry(date(2026, 6, 1), "real", "AAA", "buy", 100, 50.0, 5.0), paths.ledger)
        paths.equity.write_text(half(EQUITY), encoding="utf-8")
        paths.alerts.write_text(garbage(ALERTS), encoding="utf-8")
        before = (paths.equity.read_bytes(), paths.alerts.read_bytes())
        text = self.run_report(paths).text
        self.assertIn("AAA: 100 adet", text)
        self.assertIn("equity.csv", text)
        self.assertIn("alerts.csv", text)
        self.assertIn("Dosyaya dokunulmadı", text)
        self.assertEqual((paths.equity.read_bytes(), paths.alerts.read_bytes()), before)

    def test_damaged_ledger_stops_the_report_with_the_reason(self):
        paths = self.paths()
        paths.ledger.write_text(half(LEDGER), encoding="utf-8")
        with self.assertRaises(PersonalFileError) as ctx:
            self.run_report(paths)
        self.assertIn("ledger.csv", str(ctx.exception))


class HealthAndBotTest(Temp):
    def test_durum_shows_damaged_files_as_critical(self):
        from core.reports import health

        ledger = self.write("ledger.csv", half(LEDGER))
        check = health.personal_files_check({ledger: load_ledger})
        self.assertEqual(check.state, health.CRIT)
        self.assertIn("ledger.csv", check.text)
        self.assertEqual(health.personal_files_check({self.root / "yok.csv": load_ledger}).state, health.OK)

    def test_bot_answers_with_the_warning(self):
        from bot import handlers

        replies = []

        async def reply_text(text):
            replies.append(text)

        update = mock.MagicMock(spec=handlers.Update)
        update.effective_message = SimpleNamespace(reply_text=reply_text)
        error = PersonalFileError(self.root / "ledger.csv", "geçersiz tarih", line=7)
        asyncio.run(handlers.on_error(update, SimpleNamespace(error=error)))
        self.assertEqual(len(replies), 1)
        self.assertIn("ledger.csv", replies[0])
        self.assertIn("satır 7", replies[0])


class LockedFileTest(Temp):
    """Windows: a CSV open in Excel cannot be written (PermissionError). The report must still go out,
    say which file was locked, and change nothing; the next run writes what was missed."""

    def paths(self):
        return DailyReportTest.paths(self)

    def run_report(self, paths):
        return DailyReportTest.run_report(self, paths)

    def test_locked_equity_and_alert_logs(self):
        paths = self.paths()
        append_entry(Entry(date(2026, 6, 1), "real", "AAA", "buy", 100, 50.0, 5.0), paths.ledger)
        real_replace = Path.replace

        def locked(self_, target):
            if Path(target).name in ("equity.csv", "alerts.csv"):
                raise PermissionError(13, "The process cannot access the file", str(target))
            return real_replace(self_, target)

        with mock.patch.object(Path, "replace", locked), \
                mock.patch("builtins.open", side_effect=_locked_append(("alerts.csv",))):
            text = self.run_report(paths).text
        self.assertIn("AAA: 100 adet", text)
        self.assertIn("equity.csv kilitli", text)
        self.assertIn("Excel", text)

    def test_full_disk(self):
        import errno

        paths = self.paths()
        append_entry(Entry(date(2026, 6, 1), "real", "AAA", "buy", 100, 50.0, 5.0), paths.ledger)
        real_replace = Path.replace

        def full(self_, target):
            if Path(target).name == "equity.csv":
                raise OSError(errno.ENOSPC, "No space left on device", str(target))
            return real_replace(self_, target)

        with mock.patch.object(Path, "replace", full):
            text = self.run_report(paths).text
        self.assertIn("AAA: 100 adet", text)  # the report still goes out (sending needs no disk)
        self.assertIn("equity.csv yazılamadı: disk dolu", text)

    def test_locked_paper_orders(self):
        paths = self.paths()
        paths.orders.write_text(ORDERS.replace("BBB.IS", "AAA.IS"), encoding="utf-8")
        before = paths.orders.read_bytes()
        real_replace = Path.replace

        def locked(self_, target):
            if Path(target).name == "orders.csv":
                raise PermissionError(13, "The process cannot access the file", str(target))
            return real_replace(self_, target)

        with mock.patch.object(Path, "replace", locked):
            text = self.run_report(paths).text
        self.assertIn("orders.csv kilitli", text)
        self.assertEqual(paths.orders.read_bytes(), before)  # still pending: filled on the next run


_real_open = open


def _locked_append(names):
    def fake(file, mode="r", *a, **k):
        if "a" in mode and Path(file).name in names:
            raise PermissionError(13, "The process cannot access the file", str(file))
        return _real_open(file, mode, *a, **k)
    return fake


class CutLastLineTest(Temp):
    """Power cut while a row was being appended: the file ends without a newline. The next append
    must start on its own line, or that good row is glued to the broken one and lost too."""

    def test_run_log(self):
        from datetime import datetime

        from core.market.calendar import ISTANBUL
        from core.reports import runs

        path = self.write("runs.csv", "started_at,finished_at,data_day,status,detail\n"
                                      "2026-10-26T18:30:01+03:00,2026-10-26T18:31:00+03:00,2026-10-26,sent,\n"
                                      "2026-10-27T18:30:01+03:00,2026-10-2")
        runs.record_run(datetime(2026, 10, 28, 18, 30, tzinfo=ISTANBUL), runs.SENT, date(2026, 10, 28), path=path)
        self.assertTrue(runs.already_sent(date(2026, 10, 28), path))
        self.assertEqual(runs.read_runs(path)[-1].data_day, "2026-10-28")

    def test_signal_log(self):
        from core.signals_log import log_signal

        path = self.write("signal_log.csv", half(SIGNAL))
        from datetime import datetime

        from core.market.calendar import ISTANBUL

        log_signal("daily", "AAA.IS", 75, "Pozitif", date(2026, 10, 2), price=11, path=path,
                   now=datetime(2026, 10, 2, 18, 30, tzinfo=ISTANBUL))
        last = path.read_text(encoding="utf-8").splitlines()[-1]
        self.assertTrue(last.startswith("2026-10-02T18:30:00+03:00,daily,AAA.IS,75,"), last)

    def test_bot_says_which_file_is_locked(self):
        from bot import handlers

        replies = []

        async def reply_text(text):
            replies.append(text)

        update = mock.MagicMock(spec=handlers.Update)
        update.effective_message = SimpleNamespace(reply_text=reply_text)
        error = PermissionError(13, "The process cannot access the file", str(self.root / "ledger.csv"))
        asyncio.run(handlers.on_error(update, SimpleNamespace(error=error)))
        self.assertEqual(len(replies), 1)
        self.assertIn("ledger.csv kilitli", replies[0])
        self.assertIn("kaydedilmedi", replies[0])


if __name__ == "__main__":
    unittest.main()
