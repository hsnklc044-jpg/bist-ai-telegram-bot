"""
Öz-denetim 2, Ö8: five workflows push to the research-results branch. The weekly research
runs long; if another one pushed meanwhile, its plain `git push` was rejected and the week's
results (with crosscheck/latest.json, which the accuracy SLO reads) were lost. Every push to
research-results rebases and retries.
"""

import re
import unittest
from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"


class ResultsPushRetriesTest(unittest.TestCase):
    def test_every_results_push_rebases_and_retries(self):
        pushing = [p for p in sorted(WORKFLOWS.glob("*.yml")) if re.search(r"git push( -q)? origin research-results", p.read_text("utf-8"))]
        self.assertGreaterEqual(len(pushing), 5)
        for path in pushing:
            text = path.read_text(encoding="utf-8")
            with self.subTest(path.name):
                self.assertNotRegex(text, r"(?m)^\s*git push origin research-results\s*$")  # a bare, one-shot push
                self.assertIn("git pull --rebase -q origin research-results", text)
                self.assertTrue(re.search(r"for i in 1 2 3|foreach \(\$i in 1\.\.3\)", text))


if __name__ == "__main__":
    unittest.main()
