"""
M31 re-validation (04.11.2026, docs/validation/M31.md): the findings fixed without touching the
K-63/K-64/K-68 evaluation code or the 03.02.2027 forward test.

Y1/O3  an unvalidated card does not present its score as a confidence nor its lots as a trade size
O1     the live model never learns from the holdout (02.11.2026 and after)
O2     the card names the session it would enter at
D1     a stale model that could not be retrained says so
D2     cards of the same day share the free cash
D5     an untracked .py file makes the code stamp "not clean"
D8     the result files carry the data and code stamp
"""

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date
from io import StringIO
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

from core.screen import ai
from core.signals import store as S


def candidate(proba=0.8, close=100.0, day=date(2026, 11, 3)):
    return ai.Candidate("THYAO.IS", close, 30.0, 15.0, 0.05, -0.1, proba, lots=10, box=100_000.0,
                        candle_day=day)


class CardWordingTest(unittest.TestCase):
    def test_unvalidated_card_does_not_sell_its_score_or_lots(self):
        text = ai.message(candidate(), False)
        self.assertNotIn("ML güven skoru", text)
        self.assertIn("Model skoru (kalibre değil, olasılık değildir):</b> %80", text)
        self.assertIn("yalnız sanal defter", text)

    def test_validated_card_keeps_its_wording(self):
        text = ai.message(candidate(), True)
        self.assertIn("ML güven skoru", text)
        self.assertNotIn("yalnız sanal defter", text)

    def test_card_names_the_entry_session(self):
        # candle of Tuesday 03.11.2026: the entry is the next session's open, Wednesday 04.11.2026
        self.assertIn("ertesi seans açılışı (04.11.2026)", ai.message(candidate(), False))


class LiveModelHoldoutTest(unittest.TestCase):
    def test_live_model_stops_before_the_holdout(self):
        from core.backtest.run import HOLDOUT_START
        from core.ml import signal_filter as SF
        from tests.test_signal_filter import daily

        frames = {f"R{i}.IS": daily(1500, 60 + i) for i in range(30)}
        seen = {}

        def make(rows):
            seen["rows"] = rows
            return SF.fit(rows, trees=5)

        idx = frames["R0.IS"].index
        with tempfile.TemporaryDirectory() as tmp:
            shifted = {s: df.set_axis(pd.bdate_range(end="2026-12-15", periods=len(df))) for s, df in frames.items()}
            SF.fit_live(shifted, None, date(2026, 12, 15), Path(tmp) / "m.joblib", make=make)
        self.assertGreater(len(seen["rows"]), 0)
        self.assertLess(seen["rows"]["time"].max(), HOLDOUT_START)
        self.assertLess(seen["rows"]["label_end"].max(), HOLDOUT_START)
        self.assertGreater(len(idx), 0)


class StaleModelTest(unittest.TestCase):
    def test_a_stale_model_that_could_not_be_retrained_is_named(self):
        from core.ml import signal_filter as SF

        old = {"model": None, "trained": "2026-10-01", "rows": 100, "params": {}}
        with mock.patch.object(SF, "load_live", return_value=old), \
                mock.patch.object(SF, "_daily", return_value=({}, None)), \
                mock.patch.object(SF, "fit_live", return_value=0), \
                mock.patch.object(SF, "validated", return_value=False), \
                mock.patch("core.reports.daily.adjusted_bars", return_value=pd.DataFrame()):
            out = ai.live(date(2026, 11, 3))
        self.assertIn("01.10.2026", out[0][0])
        self.assertIn("yeniden eğitilemedi", out[0][0])


class SharedCashTest(unittest.TestCase):
    def test_cards_of_one_day_share_the_free_cash(self):
        class Fixed:
            def predict_proba(self, x):
                return np.array([[0.2, 0.8]])

        rng = np.random.default_rng(0)
        close = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, 400)))
        df = pd.DataFrame({"open": close, "high": close * 1.01, "low": close * 0.99, "close": close,
                           "volume": 1e6}, index=pd.bdate_range("2025-01-01", periods=400))
        frames = {f"{c}.IS": df for c in ("A", "B", "C", "D", "E", "F")}
        with mock.patch("core.market.extended.trigger_mask",
                        side_effect=lambda ind: pd.Series(True, index=ind.index)), \
                tempfile.TemporaryDirectory() as tmp:
            book = Path(tmp) / "signals.db"
            ai.run(date(2026, 11, 3), frames, Fixed(), validated=False, book=book)
            conn = S.connect(book)
            cards = S.signals(conn)
            conn.close()
        cost = sum((c.qty or 0) * c.signal_close for c in cards)
        self.assertLessEqual(cost, S.CAPITAL + 1e-6)  # never more than the cash box, all cards together
        self.assertLess(len(cards), len(frames))      # the last ones find no free cash left


class CodeStampTest(unittest.TestCase):
    def test_untracked_python_file_is_not_clean(self):
        from core.analytics import provenance as P

        def git(root, *args):
            if args[0] == "rev-parse":
                return "abc"
            if "--untracked-files=no" in args:
                return ""
            return "?? core/new_module.py"

        with mock.patch.object(P, "_git", side_effect=git):
            code = P.code_version()
        self.assertFalse(code.clean)

    def test_stamp_names_python_and_key_libraries(self):
        from core.analytics import provenance as P

        line = P.code_version().line()
        self.assertIn("Python 3.", line)
        self.assertIn("pandas ", line)
        self.assertIn("scikit-learn ", line)


class ResultFileStampTest(unittest.TestCase):
    def test_result_files_carry_the_stamp_and_still_load(self):
        from core.analytics import card_study, dip_study
        from core.ml import signal_filter

        with tempfile.TemporaryDirectory() as tmp:
            logs = Path(tmp)
            with mock.patch("core.config.paths.LOG_DIR", logs), redirect_stdout(StringIO()), \
                    mock.patch("core.market.hourly.load_hourly",
                               return_value=mock.Mock(frames={}, summary=lambda: "")):
                dip_study.main([])
                signal_filter.main(["--zaman", "saatlik"])
            for name in ("dip_study.json", "signal_filter_saatlik.json"):
                got = json.loads((logs / name).read_text(encoding="utf-8"))
                self.assertIn("provenance", got, name)
                self.assertIn("sha256", got["provenance"]["data"])
                self.assertIn("commit", got["provenance"]["code"])
            # the readers still accept a file with the extra key
            with mock.patch.object(signal_filter, "report_file", return_value=logs / "signal_filter_saatlik.json"):
                self.assertFalse(signal_filter.validated("saatlik"))
            card = logs / "card_study.json"
            payload = {**card_study.asdict(card_study.RECORDED), "interval": [0, 0],
                       "provenance": {"data": {}, "code": {}}}
            card.write_text(json.dumps(payload), encoding="utf-8")
            with mock.patch.object(card_study, "RESULT_FILE", card):
                result, source = card_study.latest()
            self.assertEqual(source, "bu bilgisayardaki son ölçüm")
            self.assertEqual(result.events, card_study.RECORDED.events)


if __name__ == "__main__":
    unittest.main()
