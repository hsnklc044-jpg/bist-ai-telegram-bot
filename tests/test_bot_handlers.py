"""Telegram command handlers, end to end with fake updates (no network, private files in temp)."""

import asyncio
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from core.ledger import service
from core.market import store
from core.market.universe import BENCHMARK
from core.watchlist import repository
from tests.helpers import offline_market
from tests.test_overview import PrivateFiles

CHAT = 42


def run(handler, args=()):
    sent: list[str] = []

    async def reply_text(text, **kwargs):
        sent.append(text)

    message = SimpleNamespace(reply_text=reply_text)
    update = SimpleNamespace(message=message, effective_message=message, effective_chat=SimpleNamespace(id=CHAT))
    asyncio.run(handler(update, SimpleNamespace(args=list(args))))
    return "\n".join(sent)


class TempFiles(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        for target, name in (
            (mock.patch.object(repository, "WATCHLIST_FILE", self.root / "watchlist.json"), None),
            (mock.patch.object(service, "LEDGER_FILE", self.root / "ledger.csv"), None),
            (mock.patch.object(service, "PAPER_ORDERS_FILE", self.root / "orders.csv"), None),
            (mock.patch.object(service, "ALERTS_LOG_FILE", self.root / "alerts.csv"), None),
        ):
            target.start()
            self.addCleanup(target.stop)


class WatchlistCommandsTest(TempFiles):
    def test_usage_add_list_remove(self):
        from bot.watchlist import watchadd, watchlist, watchremove

        self.assertIn("Kullanım", run(watchadd))
        self.assertIn("Kullanım", run(watchremove))
        self.assertIn("boş", run(watchlist))

        self.assertIn("EREGL.IS watchlist'e eklendi", run(watchadd, ["eregl"]))
        bad = run(watchadd, ["../etc"])  # the validation message is shown, nothing is added
        self.assertTrue(bad)
        self.assertNotIn("eklendi", bad)
        self.assertIn("• EREGL.IS", run(watchlist))

        self.assertIn("kaldırıldı", run(watchremove, ["EREGL"]))
        self.assertIn("watchlist'te yok", run(watchremove, ["EREGL"]))

    def test_scan(self):
        from bot.watchlist import watchadd, watchscan

        self.assertIn("boş", run(watchscan))
        run(watchadd, ["THYAO"])
        with offline_market(), PrivateFiles():
            store.update([BENCHMARK, "THYAO.IS"])
            text = run(watchscan)

        self.assertIn("THYAO.IS", text)
        self.assertIn("Görünüm", text)


class PortfolioCommandsTest(TempFiles):
    def test_trade_portfolio_paper_alerts(self):
        from bot.portfolio import alerts, paper, portfolio, trade

        self.assertIn("❌", run(trade, ["al"]))
        with offline_market(), PrivateFiles():
            store.update([BENCHMARK, "THYAO.IS"])
            self.assertIn("Deftere yazıldı", run(trade, ["al", "THYAO", "10", "100", "01.10.2026"]))
            text = run(portfolio)
            self.assertIn("Gerçek hesap", text)
            self.assertIn("THYAO: 10 adet", text)
            self.assertIn("Risk:", text)

            self.assertIn("Bekleyen sanal emir yok", run(paper))
            self.assertIn("Kayda geçen", run(paper, ["al", "THYAO", "5", "deneme"]))
            self.assertIn("#1 al THYAO", run(paper))
            self.assertIn("❌", run(paper, ["sat", "THYAO", "5"]))  # nothing held in the paper account

        self.assertIn("Açık risk uyarısı yok", run(alerts))

    def test_broken_ledger_is_reported(self):
        from bot.portfolio import portfolio

        (self.root / "ledger.csv").write_text("id,date\nx,y\n", encoding="utf-8")
        self.assertIn("Defter okunamadı", run(portfolio))

    def test_report_command(self):
        from bot import portfolio

        with mock.patch.object(portfolio, "_daily_text", return_value="RAPOR"):
            text = run(portfolio.report)
        self.assertIn("hazırlanıyor", text)
        self.assertIn("RAPOR", text)


class UpdateCommandTest(unittest.TestCase):
    def test_update_and_history_option(self):
        from core.market import update

        out = io.StringIO()
        with offline_market() as provider, PrivateFiles(), \
                mock.patch.object(update, "load_universe", return_value=["AAA.IS"]), \
                mock.patch("core.market.membership.ever_members", return_value=["AAA.IS", "OLD.IS"]), \
                redirect_stdout(out):
            update.main([])
            update.main(["--bist100-history"])

        text = out.getvalue()
        self.assertIn("2 sembol güncelleniyor", text)
        self.assertIn("3 sembol güncelleniyor", text)
        self.assertIn("OLD.IS", {s for call in provider.calls for s in call[0]})


class CandidatesTest(unittest.TestCase):
    def test_three_gates_report(self):
        from core.backtest import candidates
        from core.strategy.candidates import CANDIDATES

        symbols = [f"C{i}.IS" for i in range(6)]
        one = {"breakout": (CANDIDATES["breakout"][0], [dict(entry_days=20, exit_days=10)])}
        out = io.StringIO()
        with offline_market(), PrivateFiles(), \
                mock.patch("core.backtest.run.load_universe", return_value=symbols), \
                mock.patch.object(candidates, "CANDIDATES", one), \
                mock.patch.object(candidates, "STARTS", ("2025-01-02", "2025-06-02")), \
                mock.patch.object(candidates, "WF_START", "2026-01-02"), \
                redirect_stdout(out):
            store.update([BENCHMARK, *symbols])
            candidates.main(["--positions", "3"])

        text = out.getvalue()
        self.assertIn("breakout", text)
        self.assertIn("Kapılar", text)
        self.assertRegex(text, r"breakout .* [✓✗] [✓✗] [✓✗]")


if __name__ == "__main__":
    unittest.main()
