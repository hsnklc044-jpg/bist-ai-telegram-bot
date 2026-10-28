"""
MATURITY S4 "backtest–canlı sapması nedenleriyle raporlanmış": when a mature view drifts from
its backtest reference, the report tests the usual causes itself (a few stocks, one day, a
different market, a corporate action) instead of leaving them to be guessed later.
"""

import unittest
from datetime import date

import numpy as np
import pandas as pd

from core.market.corrections import CorporateAction
from core.reports import drift

REF = {"mean": 0.01, "period_start": "2023-08-01", "period_end": "2026-10-16"}
DAYS = pd.bdate_range("2026-11-02", periods=60)


def rows(excess_of, symbols=10, horizon=5, seed=1):
    rng = np.random.default_rng(seed)
    out = []
    for d in DAYS:
        for i in range(symbols):
            symbol = f"S{i}.IS"
            out.append({"day": d.date(), "symbol": symbol, "horizon": horizon, "view": "Pozitif",
                        "excess": excess_of(symbol, d) + rng.normal(0, 0.002)})
    return pd.DataFrame(out)


def bench(start="2023-01-02", end="2027-03-31", drift_per_day=0.0005):
    index = pd.bdate_range(start, end)
    return pd.Series(100 * np.exp(drift_per_day * np.arange(len(index))), index=index)


class ConcentrationTest(unittest.TestCase):
    def test_a_few_stocks_explain_the_drift(self):
        data = rows(lambda s, d: -0.25 if s == "S3.IS" else 0.01)
        text = "\n".join(drift.reasons(data, REF, bench()))
        self.assertIn("birkaç hisseden", text)
        self.assertIn("S3", text)

    def test_broad_drift_is_not_blamed_on_stocks_or_a_day(self):
        text = "\n".join(drift.reasons(rows(lambda s, d: -0.02), REF, bench()))
        self.assertIn("çıkarılınca da sürüyor: geniş tabanlı", text)
        self.assertIn("tek bir güne bağlı değil", text)


class OneDayTest(unittest.TestCase):
    def test_one_extreme_day(self):
        crash = DAYS[30].date()
        data = rows(lambda s, d: -0.6 if d.date() == crash else 0.01)
        text = "\n".join(drift.reasons(data, REF, bench()))
        self.assertIn(f"tek bir günden ({crash:%d.%m.%Y})", text)


class MarketAndActionsTest(unittest.TestCase):
    def test_market_numbers_for_both_periods(self):
        text = "\n".join(drift.reasons(rows(lambda s, d: -0.02), REF, bench()))
        self.assertIn("Piyasa: XU100'ün 5 seanslık ortalama getirisi canlı dönemde", text)
        self.assertIn("geçmiş dönemde", text)

    def test_corporate_actions_inside_the_window_only(self):
        actions = [CorporateAction("S2.IS", date(2026, 12, 1), factor=2.0),
                   CorporateAction("S2.IS", date(2025, 1, 2), factor=2.0),     # before
                   CorporateAction("ZZZ.IS", date(2026, 12, 1), factor=2.0)]   # not measured
        text = "\n".join(drift.reasons(rows(lambda s, d: -0.02), REF, bench(), actions))
        self.assertIn("S2 01.12.2026", text)
        self.assertNotIn("2025", text.split("Kurumsal")[-1])
        self.assertNotIn("ZZZ", text)
        quiet = "\n".join(drift.reasons(rows(lambda s, d: -0.02), REF, bench(), []))
        self.assertIn("kayıtlı kurumsal işlem yok", quiet)


class ReportTest(unittest.TestCase):
    """/performans shows the tested causes under a drifting view, and only there."""

    def test_reasons_under_the_drift_line(self):
        import tempfile
        from pathlib import Path
        from unittest import mock

        from core.reports import forward

        data = rows(lambda s, d: -0.25 if s == "S3.IS" else 0.01).assign(source=forward.SYSTEMATIC)
        close = bench()
        frame = pd.DataFrame({"open": close, "close": close})
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        expectations = Path(tmp.name) / "exp.csv"
        expectations.write_text(
            "view,horizon,mean,hit_rate,days,records,period_start,period_end,universe,generated\n"
            "Pozitif,5,0.01,0.5,800,15000,2023-08-01,2026-10-16,pit,2026-10-27\n", encoding="utf-8")
        with mock.patch.object(forward, "score_log", return_value=data), \
                mock.patch("core.market.corrections.load_corporate_actions", return_value=[]):
            text = forward.forward_report(Path(tmp.name) / "signal_log.csv", Path(tmp.name) / "equity.csv",
                                          bars=lambda s: frame, expectations_path=expectations)
        self.assertIn("anlamlı sapma", text)
        self.assertIn("neden? Sapma birkaç hisseden geliyor: S3", text)
        self.assertIn("neden? Ölçülen hisselerde bu dönemde kayıtlı kurumsal işlem yok", text)


if __name__ == "__main__":
    unittest.main()
