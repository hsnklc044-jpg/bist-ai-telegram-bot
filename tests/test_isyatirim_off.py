"""
D13 (DECISIONS K-54): İş Yatırım's robots.txt disallows /_layouts/ for every bot, and the second
source lives under it. Automated requests are switched off at one place; nothing asks the site,
the weekly summary says the source is off, and the accuracy SLO says why it is unknown.
"""

import json
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock

from core.market import crosscheck
from core.reports import slo


class SwitchTest(unittest.TestCase):
    def test_off_by_default_and_no_request_no_wait(self):
        self.assertFalse(crosscheck.ENABLED)
        self.assertIn("robots.txt", crosscheck.DISABLED_REASON)
        waited = []
        with mock.patch("requests.get", side_effect=AssertionError("must not be called")):
            with self.assertRaises(crosscheck.SourceDisabled):
                crosscheck.fetch_isyatirim("THYAO", date(2026, 10, 1), date(2026, 10, 28), sleep=waited.append)
        self.assertEqual(waited, [])

    def test_an_injected_source_still_works(self):
        # the comparison logic stays tested with recorded data (no network)
        frame = crosscheck.fetch_isyatirim("THYAO", date(2026, 10, 1), date(2026, 10, 2),
                                           get=lambda *a, **k: mock.Mock(status_code=200, json=lambda: {"ok": True, "value": []},
                                                                         raise_for_status=lambda: None))
        self.assertTrue(frame.empty)

    def test_summary_and_slo(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "latest.json"
            crosscheck.main(["--days", "30", "--summary", str(out)])
            data = json.loads(out.read_text(encoding="utf-8"))
        self.assertTrue(data["disabled"])
        result = slo.accuracy(datetime(2026, 10, 29, 20), data)
        self.assertEqual(result.state, slo.UNKNOWN)
        self.assertIn("D13", result.text)


if __name__ == "__main__":
    unittest.main()
