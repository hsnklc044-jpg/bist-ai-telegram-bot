"""scripts/veri_farki.py: counts only (no K-64 run, no return), on synthetic snapshots."""

import importlib.util
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd

PATH = Path(__file__).resolve().parents[1] / "scripts" / "veri_farki.py"
spec = importlib.util.spec_from_file_location("veri_farki", PATH)
V = importlib.util.module_from_spec(spec)
spec.loader.exec_module(V)


def hourly(days, drop_last=(), zero=0):
    stamps = [pd.Timestamp(f"{d} {h:02d}:30", tz="Europe/Istanbul") for d in days for h in range(9, 18)
              if not (d in drop_last and h == 17)]
    df = pd.DataFrame({"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 100.0}, index=pd.DatetimeIndex(stamps))
    df.iloc[:zero, 4] = 0.0
    return df


class HourlyTest(unittest.TestCase):
    def test_missing_last_candle_and_zero_volume(self):
        days = ["2026-10-26", "2026-10-27", "2026-10-28"]  # 28.10 is a half day? only full-day sessions counted below
        got = V.hourly_counts({"A.IS": hourly(["2026-10-26", "2026-10-27"], drop_last=["2026-10-27"], zero=3)})
        self.assertEqual(got["sifir_hacim"], 3)
        self.assertGreaterEqual(got["son_mum_eksik"], 1)
        self.assertGreaterEqual(got["eksik_seans"], 1)
        self.assertEqual(len(days), 3)


class DailyTest(unittest.TestCase):
    def test_elimination_lists_compared(self):
        idx = pd.bdate_range("2026-01-02", periods=60)
        rng = np.random.default_rng(0)
        from core.market.membership import members_on

        codes = sorted(members_on(idx[-1].date()))[:10]
        a = {f"{c}.IS": pd.DataFrame({"open": 10.0, "high": 10.0, "low": 10.0, "close": 10.0,
                                      "volume": rng.uniform(1e5, 1e6, 60)}, index=idx) for c in codes}
        b = {s: df.copy() for s, df in a.items()}
        first = sorted(b)[0]
        b[first]["volume"] = 1.0  # drops to the bottom of the turnover ranking in B only
        got = V.daily_counts(a, b)
        self.assertEqual(got["farkli_hisse"], 1)
        self.assertGreater(got["eleme_listesi_farkli_ay"], 0)

    def test_main_prints_counts_only(self):
        from core.analytics import provenance as P

        with tempfile.TemporaryDirectory() as tmp:
            for n in "ab":
                P.freeze({"A.IS": hourly(["2026-10-26", "2026-10-27"])}, Path(tmp) / n, None)
            with redirect_stdout(StringIO()) as out:
                self.assertEqual(V.main(["saatlik", str(Path(tmp) / "a"), str(Path(tmp) / "b")]), 0)
        self.assertIn("getiri hesaplanmadı", out.getvalue())


if __name__ == "__main__":
    unittest.main()
