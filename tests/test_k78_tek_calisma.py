"""scripts/k78_tek_calisma.py: the K-78 one-run guard, on made-up Actions records."""

import importlib.util
import os
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

PATH = Path(__file__).resolve().parents[1] / "scripts" / "k78_tek_calisma.py"
spec = importlib.util.spec_from_file_location("k78_tek_calisma", PATH)
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)


def job(name, conclusion):
    return {"name": name, "steps": [{"name": G.STEPS[name], "conclusion": conclusion}]}


class DecideTest(unittest.TestCase):
    def test_first_run_may_go(self):
        self.assertTrue(G.decide([], "measure")[0])

    def test_success_stops_the_same_step_only(self):
        self.assertFalse(G.decide([job("measure", "success")], "measure")[0])
        self.assertTrue(G.decide([job("snapshot", "success")], "measure")[0])

    def test_one_repeat_after_a_failure(self):
        self.assertTrue(G.decide([job("snapshot", "failure")], "snapshot")[0])
        self.assertFalse(G.decide([job("snapshot", "failure"), job("snapshot", "cancelled")], "snapshot")[0])

    def test_a_job_stopped_before_the_step_is_not_an_attempt(self):
        refused = [job("snapshot", "skipped"), job("snapshot", "skipped"), job("snapshot", None)]
        self.assertTrue(G.decide(refused, "snapshot")[0])


class MainTest(unittest.TestCase):
    env = {"GITHUB_REPOSITORY": "o/r", "GITHUB_TOKEN": "t", "GITHUB_RUN_ID": "9"}

    def run_with(self, get, arg="measure"):
        with mock.patch.dict(os.environ, self.env), redirect_stdout(StringIO()) as out:
            return G.main([arg], get), out.getvalue()

    def test_reads_every_page_and_skips_the_current_run(self):
        calls = []

        def get(url, _token):
            calls.append(url)
            if "/workflows/" in url:
                if url.endswith("&page=1"):
                    return {"workflow_runs": [{"id": 9}] + [{"id": i} for i in range(1, 100)]}
                return {"workflow_runs": [{"id": 100}]}
            return {"jobs": [job("measure", "success")] if "/runs/100/" in url else []}

        code, text = self.run_with(get)
        self.assertEqual(code, 1)
        self.assertIn("başarıyla", text)
        self.assertFalse(any("/runs/9/" in c for c in calls))

    def test_unreadable_record_stops(self):
        def get(_url, _token):
            raise OSError("down")

        code, text = self.run_with(get)
        self.assertEqual(code, 1)
        self.assertIn("okunamadı", text)

    def test_wrong_argument(self):
        with redirect_stdout(StringIO()):
            self.assertEqual(G.main(["x"]), 2)

    def test_allowed_returns_zero(self):
        code, _ = self.run_with(lambda url, _t: {"workflow_runs": []} if "/workflows/" in url else {"jobs": []})
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
