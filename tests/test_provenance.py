"""
Measurement provenance (K-76): every measurement prints its data range, candle count, data hash and
code commit; a frozen snapshot reads back as the same data; the same data gives the same report twice.
"""

import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd

from core.analytics import provenance as P

TZ = "Europe/Istanbul"


def hourly(seed: int, n: int = 900, start: str = "2026-01-05 09:30") -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start, periods=n, freq="h", tz=TZ)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    open_ = close * (1 + rng.normal(0, 0.002, n))
    high = np.maximum(open_, close) * (1 + rng.uniform(0, 0.004, n))
    low = np.minimum(open_, close) * (1 - rng.uniform(0, 0.004, n))
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close,
                         "volume": rng.integers(1_000, 9_000, n).astype(float)}, index=idx)


def frames():
    return {"AAA.IS": hourly(1), "BBB.IS": hourly(2), "CCC.IS": hourly(3, start="2026-02-02 09:30")}


class DigestTest(unittest.TestCase):
    def test_order_and_copy_do_not_change_the_hash(self):
        f = frames()
        backwards = {t: f[t].copy()[["close", "volume", "open", "low", "high"]] for t in reversed(list(f))}
        self.assertEqual(P.digest(f), P.digest(backwards))

    def test_one_value_or_one_candle_changes_the_hash(self):
        f = frames()
        g = {t: df.copy() for t, df in f.items()}
        g["BBB.IS"].iloc[10, 3] += 0.01
        self.assertNotEqual(P.digest(f), P.digest(g))
        h = {t: df.copy() for t, df in f.items()}
        h["AAA.IS"] = h["AAA.IS"].iloc[1:]
        self.assertNotEqual(P.digest(f), P.digest(h))

    def test_describe_cuts_like_the_studies(self):
        f = frames()
        edge = pd.Timestamp("2026-02-01")
        data = P.describe(f, edge)
        expected = sum(int((df.index < edge.tz_localize(TZ)).sum()) for df in f.values())
        self.assertEqual(data.candles, expected)
        self.assertEqual(data.stocks, 2)  # CCC starts after the edge
        self.assertIn("01.02.2026 öncesi", data.line())
        count = f"{expected:,}".replace(",", ".")
        self.assertGreater(expected, 1000)
        self.assertTrue(data.line().startswith(f"Veri: 2 hisse, {count} mum, 05.01.2026 09:30 – "), data.line())
        self.assertIn(data.sha256, data.line())


class SnapshotTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def test_freeze_then_thaw_is_the_same_data(self):
        f = frames()
        edge = pd.Timestamp("2026-02-10")
        data = P.freeze(f, self.dir / "a", edge, source="test")
        back = P.thaw(self.dir / "a")
        self.assertEqual(P.digest(back), data.sha256)
        self.assertEqual(P.describe(f, edge).sha256, data.sha256)
        for t, df in back.items():
            self.assertTrue(all(ts < edge.tz_localize(TZ) for ts in df.index))
            self.assertEqual(str(df.index.tz), TZ)

    def test_the_same_data_gives_the_same_file(self):
        P.freeze(frames(), self.dir / "a", None)
        P.freeze(frames(), self.dir / "b", None)
        self.assertEqual((self.dir / "a" / P.SNAPSHOT).read_bytes(), (self.dir / "b" / P.SNAPSHOT).read_bytes())

    def test_a_changed_file_is_refused(self):
        P.freeze(frames(), self.dir / "a", None)
        path = self.dir / "a" / P.SNAPSHOT
        path.write_bytes(path.read_bytes()[:-8] + b"\0" * 8)
        with self.assertRaises(P.SnapshotError):
            P.thaw(self.dir / "a")

    def test_a_changed_manifest_hash_is_refused(self):
        import json

        P.freeze(frames(), self.dir / "a", None)
        m = P.manifest(self.dir / "a")
        m["data"]["sha256"] = "0" * 64
        (self.dir / "a" / P.MANIFEST).write_text(json.dumps(m), encoding="utf-8")
        with self.assertRaises(P.SnapshotError):
            P.thaw(self.dir / "a")

    def test_daily_frames_without_time_zone(self):
        idx = pd.date_range("2025-01-02", periods=300, freq="B")
        df = hourly(4, 300).set_axis(idx)
        P.freeze({"X.IS": df}, self.dir / "d", None)
        back = P.thaw(self.dir / "d")
        self.assertIsNone(back["X.IS"].index.tz)
        self.assertEqual(P.digest(back), P.digest({"X.IS": df}))

    def test_show_command(self):
        P.freeze(frames(), self.dir / "a", None, source="deneme")
        out = StringIO()
        with redirect_stdout(out):
            self.assertEqual(P.main(["show", str(self.dir / "a")]), 0)
        self.assertIn("sha256", out.getvalue())
        self.assertIn("deneme", out.getvalue())


class DailyStoreTest(unittest.TestCase):
    def test_daily_store_is_described_and_frozen_before_the_holdout(self):
        from unittest import mock

        idx = pd.date_range("2026-09-01", "2026-11-04", freq="B")
        df = hourly(5, len(idx)).set_axis(idx)
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(P, "daily_frames", return_value={"X.IS": df}):
            out = StringIO()
            with redirect_stdout(out):
                self.assertEqual(P.main(["daily"]), 0)
                self.assertEqual(P.main(["freeze-daily", str(Path(tmp) / "d")]), 0)
            back = P.thaw(Path(tmp) / "d")
        self.assertIn("Günlük fiyat deposu Veri: 1 hisse", out.getvalue())
        self.assertIn("02.11.2026 öncesi", out.getvalue())
        self.assertLess(back["X.IS"].index.max(), pd.Timestamp("2026-11-02"))


class CompareTest(unittest.TestCase):
    def test_same_data(self):
        self.assertIn("birebir aynı", P.compare_text(frames(), frames()))

    def test_differences_are_listed_stock_by_stock(self):
        a = frames()
        b = {t: df.copy() for t, df in a.items()}
        b["AAA.IS"] = b["AAA.IS"].iloc[5:]           # window moved: 5 candles only in A
        b["BBB.IS"].iloc[100, 3] *= 1.01              # one candle revised
        del b["CCC.IS"]                               # a stock missing
        diff = P.compare(a, b).set_index("hisse")
        self.assertEqual(diff.loc["AAA.IS", "yalniz_a"], 5)
        self.assertEqual(diff.loc["AAA.IS", "degisen"], 0)
        self.assertEqual(diff.loc["BBB.IS", "degisen"], 1)
        self.assertEqual(diff.loc["CCC.IS", "mum_b"], 0)
        self.assertIn("3 hissede fark var", P.compare_text(a, b))


class CodeTest(unittest.TestCase):
    def test_code_version_names_the_imported_core(self):
        import core

        code = P.code_version()
        self.assertEqual(code.version, core.__version__)
        self.assertEqual(Path(code.path), Path(core.__file__).resolve().parent)
        self.assertIn(f"v{core.__version__}", code.line())

    def test_no_git_is_said_plainly(self):
        from unittest import mock

        with mock.patch.object(P, "_git", return_value=None):
            code = P.code_version()
        self.assertEqual(code.commit, "bilinmiyor")
        self.assertIsNone(code.clean)
        self.assertIn("durum bilinmiyor", code.line())


class RepeatTest(unittest.TestCase):
    """The same frozen data run twice gives the same report (dip study K-63, signal layer K-64)."""

    def test_dip_study_twice(self):
        from core.analytics.dip_study import study, text

        f = frames()
        edge = pd.Timestamp("2026-03-01").tz_localize(TZ)
        self.assertEqual(text(study(f, edge)), text(study(f, edge)))

    def test_signal_layer_twice_on_thawed_data(self):
        """Big enough that the model is really trained and tested (a few trees keep it fast)."""

        from core.ml.signal_filter import SPEC, evaluate, events, fit, text

        data = {f"S{i}.IS": hourly(10 + i, 3000, "2025-11-05 09:30") for i in range(8)}
        with tempfile.TemporaryDirectory() as tmp:
            P.freeze(data, Path(tmp), None)
            once = P.thaw(Path(tmp))
            twice = P.thaw(Path(tmp))
        x, y = SPEC["saatlik"]

        def run(f):
            report = evaluate(events(f, x, y, None, None), "saatlik", make=lambda train: fit(train, trees=15))
            return report, text(report)

        (report, first), (_, second), (_, direct) = run(once), run(twice), run(data)
        self.assertGreater(report.tested, 0)
        self.assertEqual(P.report_digest(first), P.report_digest(second))
        self.assertEqual(first, direct)  # the snapshot changes nothing the study sees

    def test_mains_print_provenance_first(self):
        from unittest import mock

        from core.analytics import dip_study
        from core.ml import signal_filter

        with tempfile.TemporaryDirectory() as tmp:
            P.freeze(frames(), Path(tmp) / "s", None)
            with mock.patch("core.config.paths.LOG_DIR", Path(tmp) / "logs"):
                for run in (lambda: dip_study.main(["--veri", str(Path(tmp) / "s")]),
                            lambda: signal_filter.main(["--zaman", "saatlik", "--veri", str(Path(tmp) / "s")])):
                    out = StringIO()
                    with redirect_stdout(out):
                        self.assertEqual(run(), 0)
                    lines = out.getvalue().splitlines()
                    self.assertTrue(lines[0].startswith("Veri: "), lines[:3])
                    self.assertIn("sha256", lines[0])
                    self.assertTrue(lines[1].startswith("Kod: v"), lines[:3])
                    self.assertTrue(any(line.startswith("Rapor sha256 ") for line in lines))


if __name__ == "__main__":
    unittest.main()
