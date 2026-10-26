import tempfile
import unittest
from pathlib import Path

from core.backtest import history


def _record(strategy, cagr, verdict, universe="pit"):
    return {
        "universe": universe, "period_start": "2023-08-01", "period_end": "2026-10-23",
        "strategy": strategy, "cagr": cagr, "max_drawdown": -0.3, "sharpe": 0.5, "trades": 10,
        "excess": 0.01 if verdict else None, "excess_low": -0.1 if verdict else None,
        "excess_high": 0.2 if verdict else None, "level": 0.99 if verdict else None, "verdict": verdict,
    }


class HistoryTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "history.csv"

    def test_missing_and_first_run(self):
        self.assertIn("yok", history.compare(self.path))

        history.append_records([_record("Trend", 0.30, "anlamlı değil"), _record("XU100 al-tut", 0.14, "")],
                               self.path, run_date="2026-10-24")
        text = history.compare(self.path)
        self.assertIn("İlk kayıt", text)
        self.assertIn("Trend: yıllık +30.0% | anlamlı değil; anlamlı yüksek 0/1 çalışmada", text)
        self.assertIn("XU100 al-tut: yıllık +14.0%", text)

    def test_week_over_week_and_verdict_change(self):
        history.append_records([_record("Trend", 0.30, "anlamlı değil")], self.path, run_date="2026-10-24")
        history.append_records([_record("Trend", 0.35, history.SIGNIFICANT),
                                _record("Trend", 0.20, "anlamlı değil", universe="today")],
                               self.path, run_date="2026-10-31")

        text = history.compare(self.path)
        self.assertIn("2 çalışma, son 2026-10-31, önceki 2026-10-24", text)
        self.assertIn("yıllık +35.0% (önceki +30.0%) ⚠️ karar değişti", text)
        self.assertIn("anlamlı yüksek 1/2 çalışmada", text)
        self.assertIn("[bugünkü liste]", text)
        self.assertIn("tek bir haftanın", text)

    def test_appends_without_rewriting(self):
        history.append_records([_record("A", 0.1, "")], self.path, run_date="2026-10-24")
        first = self.path.read_text(encoding="utf-8")
        history.append_records([_record("A", 0.2, "")], self.path, run_date="2026-10-31")
        self.assertTrue(self.path.read_text(encoding="utf-8").startswith(first))


if __name__ == "__main__":
    unittest.main()
