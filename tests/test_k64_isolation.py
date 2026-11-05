"""
K-79 (user's request 05.11.2026, A1): two claims turned into tests.

1. The K-64 measurement (signal_filter.main -> evaluate(events(...))) never loads, trains or writes the
   live /tara ai model (logs/signal_model.joblib): statically, no function reachable from main() names
   load_live / fit_live / model_file / joblib; and at run time, with those made to fail, the
   measurement still runs on a frozen snapshot.
2. /tara ai can (re)train its model only through signal_filter.fit_live (the frozen rule that never
   sees the holdout): core/screen/ai.py calls no other trainer and writes no model file itself.
"""

import ast
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date
from io import StringIO
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
MODEL_NAMES = {"load_live", "fit_live", "model_file", "joblib"}


def _module(path: str):
    text = (ROOT / path).read_text(encoding="utf-8")
    return ast.parse(text)


def _names(node) -> set[str]:
    found = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Name):
            found.add(n.id)
        elif isinstance(n, ast.Attribute):
            found.add(n.attr)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            found |= {a.name.split(".")[0] for a in n.names}
            if isinstance(n, ast.ImportFrom) and n.module:
                found.add(n.module.split(".")[-1])
    return found


class MeasurementPathTest(unittest.TestCase):
    def test_nothing_reachable_from_main_touches_the_model_file(self):
        tree = _module("core/ml/signal_filter.py")
        functions = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
        reached, todo = set(), ["main"]
        while todo:
            name = todo.pop()
            if name in reached:
                continue
            reached.add(name)
            names = _names(functions[name])
            self.assertFalse(names & MODEL_NAMES, f"{name} reaches {names & MODEL_NAMES}")
            todo += [n for n in names if n in functions and n not in reached]
        self.assertTrue({"main", "evaluate", "events", "fit", "labels", "features"} <= reached)

    def test_measurement_runs_with_the_model_file_forbidden(self):
        from core.analytics import provenance as P
        from core.ml import signal_filter as S
        from tests.test_provenance import frames

        def forbidden(*args, **kwargs):
            raise AssertionError("the K-64 measurement touched the live model")

        with tempfile.TemporaryDirectory() as tmp:
            P.freeze(frames(), Path(tmp) / "s", None)
            with mock.patch.object(S, "load_live", forbidden), mock.patch.object(S, "fit_live", forbidden), \
                    mock.patch.object(S, "model_file", forbidden), mock.patch("joblib.load", forbidden), \
                    mock.patch("joblib.dump", forbidden), redirect_stdout(StringIO()) as out:
                self.assertEqual(S.main(["--zaman", "saatlik", "--veri", str(Path(tmp) / "s")]), 0)
        self.assertIn("Sinyal onay katmanı (saatlik)", out.getvalue())


class TaraAiTrainingTest(unittest.TestCase):
    def test_ai_module_trains_only_through_fit_live(self):
        tree = _module("core/screen/ai.py")
        calls = [n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
        self.assertEqual([c for c in calls if c in {"fit", "partial_fit", "fit_transform", "dump", "evaluate"}], [])
        self.assertEqual(calls.count("fit_live"), 1)
        self.assertNotIn("RandomForestClassifier", _names(tree))

    def test_stale_model_is_retrained_by_fit_live_only(self):
        from core.ml import signal_filter as S
        from core.screen import ai

        old = {"model": None, "trained": "2026-10-01", "rows": 1, "params": {}}
        with mock.patch.object(S, "load_live", return_value=old), \
                mock.patch.object(S, "_daily", return_value=({}, None)), \
                mock.patch.object(S, "fit_live", return_value=0) as fit_live, \
                mock.patch.object(S, "fit", side_effect=AssertionError("trained outside fit_live")), \
                mock.patch.object(S, "validated", return_value=False), \
                mock.patch("core.reports.daily.adjusted_bars", side_effect=lambda s: __import__("pandas").DataFrame()):
            ai.live(date(2026, 11, 5))
        fit_live.assert_called_once()

    def test_a_fresh_model_is_not_retrained(self):
        """10:36 on 05.11.2026: the model of 03.11 is 2 days old; /tara ai must not retrain it."""

        from core.ml import signal_filter as S
        from core.screen import ai

        fresh = {"model": None, "trained": "2026-11-03", "rows": 744, "params": {}}
        with mock.patch.object(S, "load_live", return_value=fresh), \
                mock.patch.object(S, "fit_live") as fit_live, \
                mock.patch.object(S, "validated", return_value=False), \
                mock.patch("core.reports.daily.adjusted_bars", side_effect=lambda s: __import__("pandas").DataFrame()):
            ai.live(date(2026, 11, 5))
        fit_live.assert_not_called()


if __name__ == "__main__":
    unittest.main()
