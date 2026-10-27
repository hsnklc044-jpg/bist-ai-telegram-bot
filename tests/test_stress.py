"""
Portfolio stress test (core/reports/stress.py): the worst 1, 5 and 20 session falls of XU100 in
the stored history, found from the data (no hand-typed event dates), applied to each holding with
its own return over the same sessions. Information only.
"""

import unittest

import pandas as pd

from core.reports import stress


def closes(values, start="2024-01-01"):
    index = pd.bdate_range(start=start, periods=len(values))
    return pd.DataFrame({"close": values}, index=index)


# XU100: flat, then a 3-day crash (-10%, -10%, -10%), then flat
XU = closes([100] * 30 + [90, 81, 72.9] + [72.9] * 30)


class WorstWindowTest(unittest.TestCase):
    def test_worst_falls_are_found_in_the_data(self):
        windows = stress.worst_windows(XU["close"], lengths=(1, 5))
        one, five = windows
        self.assertEqual(one.sessions, 1)
        self.assertAlmostEqual(one.market, -0.10)
        self.assertEqual(five.sessions, 5)
        self.assertAlmostEqual(five.market, 72.9 / 100 - 1)
        self.assertLess(five.base, five.end)

    def test_too_short_history_has_no_window(self):
        self.assertEqual(stress.worst_windows(XU["close"].head(3), lengths=(20,)), [])


class ScenarioTest(unittest.TestCase):
    def test_each_holding_with_its_own_return_or_the_market_when_missing(self):
        window = stress.worst_windows(XU["close"], lengths=(5,))[0]
        frames = {
            "AAA.IS": closes([50] * 30 + [40, 30, 25] + [25] * 30),        # fell 50%
            "NEW.IS": closes([10] * 5, start="2024-04-01"),               # listed after the crash
        }
        s = stress.scenario(window, {"AAA.IS": 1000.0, "NEW.IS": 500.0}, frames)
        rows = {r.symbol: r for r in s.rows}
        self.assertAlmostEqual(rows["AAA.IS"].change, -0.5)
        self.assertFalse(rows["AAA.IS"].assumed)
        self.assertAlmostEqual(rows["NEW.IS"].change, window.market)
        self.assertTrue(rows["NEW.IS"].assumed)
        self.assertAlmostEqual(s.loss, 1000 * -0.5 + 500 * window.market)

    def test_text(self):
        window = stress.worst_windows(XU["close"], lengths=(1,))[0]
        s = stress.scenario(window, {"AAA.IS": 1000.0}, {"AAA.IS": XU})
        text = stress.format_report([s], account="paper", total=2000.0)
        self.assertIn("Sanal hesap", text)
        self.assertIn("en kötü 1 seans", text)
        self.assertIn("XU100 -%10,0", text)
        self.assertIn("-100 TL", text)       # 1.000 × -%10
        self.assertIn("hesabın -%5,0", text)  # of 2.000 total
        self.assertIn("Bilgi amaçlıdır", text)
        self.assertIn("pozisyon yok", stress.format_report([], account="real", total=0.0))


class LiveDataTest(unittest.TestCase):
    def test_reads_holdings_and_prices_and_the_bot_command(self):
        from types import SimpleNamespace
        from unittest import mock

        from bot.handlers import COMMANDS, MENU
        from bot.reports import stress_test
        from bot.start import HELP_TEXT
        from core.reports import daily
        from tests.test_bot_handlers import run

        holding = SimpleNamespace(position=SimpleNamespace(symbol="AAA.IS"), value=1000.0)
        bars = {"AAA.IS": closes([50] * 30 + [40, 30, 25] + [25] * 30), "XU100.IS": XU}
        with mock.patch("core.ledger.load_ledger", return_value=[]), \
                mock.patch("core.ledger.cash_balance", return_value=1000.0), \
                mock.patch.object(daily, "value_holdings", return_value=([holding], 1000.0)), \
                mock.patch.object(daily, "adjusted_bars", side_effect=lambda s: bars.get(s, bars["XU100.IS"])):
            text = stress.stress_text("paper")
            self.assertTrue(run(stress_test, ["sanal"]).endswith(text))
        self.assertIn("AAA: -%50,0", text)
        self.assertIn("en kötü 20 seans", text)
        self.assertEqual(stress.parse_account(["Sanal"]), "paper")
        self.assertEqual(stress.parse_account([]), "real")
        self.assertIn("stres", dict(COMMANDS))
        self.assertIn("stres", dict(MENU))
        self.assertIn("/stres", HELP_TEXT)

        with mock.patch("core.ledger.load_ledger", return_value=[]), \
                mock.patch.object(daily, "value_holdings", return_value=([], 0.0)):
            self.assertIn("pozisyon yok", stress.stress_text("real"))


class CommandLineTest(unittest.TestCase):
    def test_main(self):
        import io
        from contextlib import redirect_stdout
        from unittest import mock

        out = io.StringIO()
        with mock.patch.object(stress, "stress_text", return_value="sonuç") as made, redirect_stdout(out):
            self.assertEqual(stress.main(["sanal"]), 0)
        made.assert_called_once_with("paper")
        self.assertIn("sonuç", out.getvalue())


if __name__ == "__main__":
    unittest.main()
