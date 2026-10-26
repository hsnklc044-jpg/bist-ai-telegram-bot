import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import pandas as pd

from core.backtest import scenarios
from core.market import corrections, store
from core.market.corrections import CorporateAction
from core.market.universe import BENCHMARK
from tests.helpers import offline_market

SYMBOLS = [f"S{i}.IS" for i in range(6)]


def panel(index, names, **_):
    return pd.DataFrame(True, index=index, columns=names)


class ScenarioTest(unittest.TestCase):
    def test_four_scenarios_and_overrides_reset(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        fixes = Path(tmp.name) / "fixes.csv"
        actions = [
            CorporateAction("S1.IS", date(2025, 9, 1), factor=0.8, source="veri incelemesi"),
            CorporateAction("S2.IS", date(2025, 9, 1), factor=0.8, source="İş Yatırım (datacheck x)"),
        ]
        with offline_market(), \
                mock.patch("core.backtest.run.load_universe", return_value=SYMBOLS), \
                mock.patch("core.market.membership.ever_members", return_value=SYMBOLS), \
                mock.patch("core.market.membership.membership_panel", side_effect=panel), \
                mock.patch.object(corrections, "load_corporate_actions", return_value=actions):
            store.update([BENCHMARK, *SYMBOLS])
            day = store.read("S3.IS").index[-30]
            fixes.write_text(f"symbol,date,factor,source,note\nS3.IS,{day.date()},0.95,x,y\n", encoding="utf-8")

            seen = []
            original = corrections.apply_corporate_actions

            def spy(df, symbol, acts=None):
                seen.append(len(acts if acts is not None else corrections._actions_override or actions))
                return original(df, symbol, acts)

            with mock.patch.object(corrections, "apply_corporate_actions", side_effect=spy):
                results = scenarios.run_scenarios(fixes, start="2025-06-01", positions=3)
            lines = scenarios.format_scenarios(results)
            candle = scenarios.candle_check(fixes)

        self.assertEqual(list(results), ["A", "B", "C", "D"])
        self.assertEqual(set(seen), {1, 2})  # A/C without the datacheck row, B/D with it
        self.assertIsNone(corrections._actions_override)
        self.assertIsNone(corrections._price_fixes)
        text = "\n".join(lines)
        self.assertIn("Bot sinyali", text)
        self.assertIn("Kazanma", text)
        self.assertIn("1 gün", "\n".join(candle))

    def test_without_fixes_only_a_and_b(self):
        with offline_market(), \
                mock.patch("core.backtest.run.load_universe", return_value=SYMBOLS), \
                mock.patch("core.market.membership.ever_members", return_value=SYMBOLS), \
                mock.patch("core.market.membership.membership_panel", side_effect=panel), \
                mock.patch.object(corrections, "load_corporate_actions", return_value=[]):
            store.update([BENCHMARK, *SYMBOLS])
            results = scenarios.run_scenarios(None, start="2025-06-01", positions=3)
        self.assertEqual(list(results), ["A", "B"])


if __name__ == "__main__":
    unittest.main()
